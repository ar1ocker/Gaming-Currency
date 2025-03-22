from datetime import timedelta

from currencies.models import CurrencyUnit, ExchangeRule, ExchangeTransaction, Service
from currencies.services import ExchangesService, HoldersService
from django import forms, views
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.validators import MinValueValidator
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator


@method_decorator(permission_required("currencies.add_exchangetransaction"), name="dispatch")
class ExchangeCreateView(views.View):
    class Form(forms.Form):
        service = forms.ModelChoiceField(Service.objects.all())
        holder_id = forms.CharField()
        exchange_rule = forms.ModelChoiceField(ExchangeRule.objects.all())
        from_unit = forms.ModelChoiceField(CurrencyUnit.objects.all())
        to_unit = forms.ModelChoiceField(CurrencyUnit.objects.all())
        from_amount = forms.IntegerField()
        auto_reject_timedelta = forms.IntegerField(validators=[MinValueValidator(180)])

    def get(self, request) -> HttpResponse:
        return render(request, "exchanges/create.html", {"form": self.Form()})

    def post(self, request) -> HttpResponse:
        form = self.Form(request.POST)

        if not form.is_valid():
            return render(request, "exchanges/create.html", {"form": form})

        holder = HoldersService.get(holder_id=form.cleaned_data["holder_id"])

        if holder is None:
            form.add_error("holder_id", "Holder with given ID does not exist")
            return render(request, "exchanges/create.html", {"form": form})

        service = form.cleaned_data["service"]
        exchange_rule = form.cleaned_data["exchange_rule"]
        from_unit = form.cleaned_data["from_unit"]
        to_unit = form.cleaned_data["to_unit"]
        from_amount = form.cleaned_data["from_amount"]
        auto_reject_timedelta = form.cleaned_data["auto_reject_timedelta"]

        try:
            exchange_transaction = ExchangesService.create(
                service=service,
                holder=holder,
                exchange_rule=exchange_rule,
                from_unit=from_unit,
                to_unit=to_unit,
                from_amount=from_amount,
                description=f"Created from admin site by {request.user.username}",
                auto_reject_timedelta=timedelta(seconds=auto_reject_timedelta),
            )
        except ExchangesService.ValidationError as e:
            form.add_error(None, e)
            return render(request, "exchanges/create.html", {"form": form})

        messages.info(request, "Transaction created")
        return HttpResponseRedirect(
            reverse("admin:currencies_exchangetransaction_change", args=[exchange_transaction.pk])
        )


@permission_required("currencies.change_exchangetransaction")
def exchange_confirm(request, object_pk):
    try:
        transaction = ExchangeTransaction.objects.get(pk=object_pk)
        ExchangesService.confirm(
            exchange_transaction=transaction, status_description=f"Confirmed from admin site by {request.user.username}"
        )
    except ExchangesService.ValidationError as e:
        messages.error(request, f"Error on confirm exchange transaction {e.message}")
    except ExchangeTransaction.DoesNotExist:
        messages.error(request, "Exchange transaction not found")
    else:
        messages.info(request, "Transaction confirmed")

    return HttpResponseRedirect(reverse("admin:currencies_exchangetransaction_change", args=[object_pk]))


@permission_required("currencies.change_exchangetransaction")
def exchange_reject(request, object_pk):
    try:
        transaction = ExchangeTransaction.objects.get(pk=object_pk)
        ExchangesService.reject(
            exchange_transaction=transaction, status_description=f"Rejected from admin site by {request.user.username}"
        )
    except ExchangesService.ValidationError as e:
        messages.error(request, f"Error on reject exchange transaction {e.message}")
    except ExchangeTransaction.DoesNotExist:
        messages.error(request, "Exchange transaction not found")
    else:
        messages.info(request, "Transaction rejected")

    return HttpResponseRedirect(reverse("admin:currencies_exchangetransaction_change", args=[object_pk]))
