from datetime import timedelta

from currencies.models import CurrencyService, TransferRule, TransferTransaction
from currencies.services import HoldersService, TransfersService
from currencies.services.accounts import AccountsService
from django import forms, views
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator


@method_decorator(permission_required("currencies.add_transfertransaction"), name="dispatch")
class TransferCreateView(views.View):
    template = "transfers/create.html"

    class Form(forms.Form):
        service = forms.ModelChoiceField(CurrencyService.objects.all())
        transfer_rule = forms.ModelChoiceField(TransferRule.objects.all())
        from_holder_id = forms.CharField()
        to_holder_id = forms.CharField()
        from_amount = forms.DecimalField(min_value=0)
        auto_reject_timedelta = forms.IntegerField(min_value=180)

    def render_form(self, request, form: forms.Form):
        return render(request, self.template, {"form": form})

    def get(self, request) -> HttpResponse:
        return self.render_form(request, self.Form())

    def post(self, request) -> HttpResponse:
        form = self.Form(request.POST)

        if not form.is_valid():
            return self.render_form(request, form)

        from_holder = HoldersService.get(holder_id=form.cleaned_data["from_holder_id"])
        if from_holder is None:
            form.add_error("from_holder_id", "Holder with given ID does not exist")
            return self.render_form(request, form)

        to_holder = HoldersService.get(holder_id=form.cleaned_data["to_holder_id"])
        if to_holder is None:
            form.add_error("to_holder_id", "Holder with given ID does not exist")
            return self.render_form(request, form)

        transfer_rule = form.cleaned_data["transfer_rule"]

        from_checking_account = AccountsService.get_or_create(holder=from_holder, currency_unit=transfer_rule.unit)[0]

        to_checking_account = AccountsService.get_or_create(holder=to_holder, currency_unit=transfer_rule.unit)[0]

        service = form.cleaned_data["service"]
        from_amount = form.cleaned_data["from_amount"]
        auto_reject_timedelta = timedelta(seconds=form.cleaned_data["auto_reject_timedelta"])

        try:
            transaction = TransfersService.create(
                service=service,
                transfer_rule=transfer_rule,
                from_checking_account=from_checking_account,
                to_checking_account=to_checking_account,
                from_amount=from_amount,
                description=f"Created from admin site by {request.user.username}",
                auto_reject_timedelta=auto_reject_timedelta,
            )
        except TransfersService.ValidationError as e:
            form.add_error(None, e)
            return self.render_form(request, form)

        messages.info(request, "Transaction created")
        return HttpResponseRedirect(reverse("admin:currencies_transfertransaction_change", args=[transaction.pk]))


@permission_required("currencies.change_transfertransaction")
def transfer_confirm(request, object_pk):
    try:
        transaction = TransferTransaction.objects.get(pk=object_pk)
        TransfersService.confirm(
            transfer_transaction=transaction, status_description=f"Confirmed from admin site by {request.user.username}"
        )
    except TransfersService.ValidationError as e:
        messages.error(request, f"Error on confirm transfer transaction {e.message}")
    except TransferTransaction.DoesNotExist:
        messages.error(request, "Transfer transaction not found")
    else:
        messages.info(request, "Transfer transaction confirmed")

    return HttpResponseRedirect(reverse("admin:currencies_transfertransaction_change", args=[object_pk]))


@permission_required("currencies.change_transfertransaction")
def transfer_reject(request, object_pk):
    try:
        transaction = TransferTransaction.objects.get(pk=object_pk)
        TransfersService.reject(
            transfer_transaction=transaction, status_description=f"Reject from admin site by {request.user.username}"
        )
    except TransfersService.ValidationError as e:
        messages.error(request, f"Error on reject transfer transaction {e.message}")
    except TransferTransaction.DoesNotExist:
        messages.error(request, "Transfer transaction not found")
    else:
        messages.info(request, "Transfer transaction rejected")

    return HttpResponseRedirect(reverse("admin:currencies_transfertransaction_change", args=[object_pk]))
