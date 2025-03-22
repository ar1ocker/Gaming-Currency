from datetime import timedelta

from currencies.models import CurrencyTransaction, CurrencyUnit, Service
from currencies.services import AccountsService, HoldersService, TransactionsService
from django import forms, views
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator


@method_decorator(permission_required("currencies.add_currencytransaction"), name="dispatch")
class TransactionCreateView(views.View):
    template = "transactions/create.html"

    class Form(forms.Form):
        service = forms.ModelChoiceField(Service.objects.all())
        holder_id = forms.CharField()
        to_unit = forms.ModelChoiceField(CurrencyUnit.objects.all())
        amount = forms.IntegerField()
        auto_reject_timedelta = forms.IntegerField(min_value=180)

    def render_form(self, request, form: forms.Form):
        return render(request, self.template, {"form": form})

    def get(self, request) -> HttpResponse:
        return self.render_form(request, self.Form())

    def post(self, request) -> HttpResponse:
        form = self.Form(request.POST)

        if not form.is_valid():
            return self.render_form(request, form)

        holder = HoldersService.get(holder_id=form.cleaned_data["holder_id"])

        if holder is None:
            form.add_error("holder_id", "Holder with given ID does not exist")
            return self.render_form(request, form)

        checking_account = AccountsService.get_or_create(holder=holder, currency_unit=form.cleaned_data["to_unit"])

        service = form.cleaned_data["service"]
        amount = form.cleaned_data["amount"]
        auto_reject_timedelta = timedelta(seconds=form.cleaned_data["auto_reject_timedelta"])

        try:
            transaction = TransactionsService.create(
                service=service,
                checking_account=checking_account,
                amount=amount,
                description=f"Create from admin site by {request.user.username}",
                auto_reject_timedelta=auto_reject_timedelta,
            )
        except TransactionsService.ValidationError as e:
            form.add_error(None, e)
            return self.render_form(request, form)

        messages.info(request, "Transaction created")
        return HttpResponseRedirect(reverse("admin:currencies_currencytransaction_change", args=[transaction.pk]))


@permission_required("currencies.change_currencytransaction")
def transaction_confirm(request, object_pk):
    try:
        transaction = CurrencyTransaction.objects.get(pk=object_pk)
        TransactionsService.confirm(
            currency_transaction=transaction, status_description=f"Confirmed from admin site by {request.user.username}"
        )
    except TransactionsService.ValidationError as e:
        messages.error(request, f"Error on confirm currency transaction {e.message}")
    except CurrencyTransaction.DoesNotExist:
        messages.error(request, "Currency Transaction not found")
    else:
        messages.info(request, "Transaction confirmed")

    return HttpResponseRedirect(reverse("admin:currencies_currencytransaction_change", args=[object_pk]))


@permission_required("currencies.change_currencytransaction")
def transaction_reject(request, object_pk):
    try:
        transaction = CurrencyTransaction.objects.get(pk=object_pk)
        TransactionsService.reject(
            currency_transaction=transaction, status_description=f"Rejected from admin site by {request.user.username}"
        )
    except TransactionsService.ValidationError as e:
        messages.error(request, f"Error on reject currency transaction {e.message}")
    except CurrencyTransaction.DoesNotExist:
        messages.error(request, "Currency Transaction not found")
    else:
        messages.info(request, "Transaction rejected")

    return HttpResponseRedirect(reverse("admin:currencies_currencytransaction_change", args=[object_pk]))
