//@ts-check
import axios from "axios";
import { subtle } from "node:crypto";
import Qs from "qs";

export default class GamingBillingAPI {
  constructor(
    endpoint,
    serviceName,
    secretKey,
    serviceHeader = "X-SERVICE",
    signatureHeader = "X-SIGNATURE",
    timestampHeader = "X-SIGNATURE-TIMESTAMP"
  ) {
    this.endpoint = endpoint;
    this.serviceName = serviceName;
    this.serviceHeader = serviceHeader;
    this.signatureHeader = signatureHeader;
    this.timestampHeader = timestampHeader;

    this.client = axios.create({ baseURL: this.endpoint });

    this._secret_key = secretKey;
    this._importedKey = null;

    this._encoder = new TextEncoder();
  }

  async _importKey() {
    this._importedKey = await subtle.importKey(
      "raw",
      this._encoder.encode(this._secret_key),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );

    this._secret_key = "";
  }

  async _computeSignatureForData(data) {
    if (this._importedKey === null) {
      await this._importKey();
    }

    //@ts-expect-error _importedKey is defined
    return Buffer.from(await subtle.sign("HMAC", this._importedKey, this._encoder.encode(data))).toString("hex");
  }

  async _getHeaders(path, data) {
    let timestamp = new Date().toISOString();

    let signature;
    if (data === undefined) {
      signature = await this._computeSignatureForData(`${timestamp}.${path}.`);
    } else {
      signature = await this._computeSignatureForData(`${timestamp}.${path}.${data}`);
    }

    return {
      [this.serviceHeader]: this.serviceName,
      [this.signatureHeader]: signature,
      [this.timestampHeader]: timestamp,
      "Content-Type": "application/json",
    };
  }

  async holdersList(filters = {}) {
    let path = "/api/currencies/holders/?" + Qs.stringify(filters, { arrayFormat: "comma" });

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async holdersDetail(holder_id) {
    let path = `/api/currencies/holders/detail/?holder_id=${holder_id}`;

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async holdersCreate(holder_id, holder_type, info = {}) {
    let path = `/api/currencies/holders/create/`;
    let data = JSON.stringify({ holder_id: holder_id, holder_type: holder_type, info: info });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async holdersUpdate(holder_id, { enabled, info }) {
    if (enabled === undefined && info === undefined) {
      throw new Error("No parameters are set");
    }

    let path = `/api/currencies/holders/update/`;
    let data = JSON.stringify({ holder_id: holder_id, enabled: enabled, info: info });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async accountsList(filters = {}) {
    let path = "/api/currencies/accounts/?" + Qs.stringify(filters, { arrayFormat: "comma" });

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async accountsDetail(holder_id, unit_symbol, holder_type) {
    let path =
      "/api/currencies/accounts/detail/?" +
      Qs.stringify(
        { holder_id: holder_id, unit_symbol: unit_symbol, holder_type: holder_type },
        { arrayFormat: "comma" }
      );

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async accountsCreate(holder_id, unit_symbol, holder_type) {
    let path = "/api/currencies/accounts/create/";

    let data = JSON.stringify({ holder_id: holder_id, unit_symbol: unit_symbol, holder_type: holder_type });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async unitsList(filters = {}) {
    let path = "/api/currencies/units/?" + Qs.stringify(filters, { arrayFormat: "comma" });

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async adjustmentsList(filters = {}) {
    let path = "/api/currencies/adjustments/?" + Qs.stringify(filters, { arrayFormat: "comma" });

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async adjustmentsCreate(holder_id, unit_symbol, amount, description, auto_reject_timeout) {
    let path = "/api/currencies/adjustments/create/";

    let data = JSON.stringify({
      holder_id: holder_id,
      unit_symbol: unit_symbol,
      amount: amount,
      description: description,
      auto_reject_timeout: auto_reject_timeout,
    });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async adjustmentsConfirm(uuid, status_description) {
    let path = "/api/currencies/adjustments/confirm/";

    let data = JSON.stringify({ uuid: uuid, status_description: status_description });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async adjustmentsReject(uuid, status_description) {
    let path = "/api/currencies/adjustments/reject/";

    let data = JSON.stringify({ uuid: uuid, status_description: status_description });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async transfersList(filters = {}) {
    let path = "/api/currencies/transfers/?" + Qs.stringify(filters, { arrayFormat: "comma" });

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async transfersCreate(from_holder_id, to_holder_id, transfer_rule, amount, description, auto_reject_timeout) {
    let path = "/api/currencies/transfers/create/";

    let data = JSON.stringify({
      from_holder_id: from_holder_id,
      to_holder_id: to_holder_id,
      transfer_rule: transfer_rule,
      amount: amount,
      description: description,
      auto_reject_timeout: auto_reject_timeout,
    });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async transfersConfirm(uuid, status_description) {
    let path = "/api/currencies/transfers/confirm/";

    let data = JSON.stringify({ uuid: uuid, status_description: status_description });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async transfersReject(uuid, status_description) {
    let path = "/api/currencies/transfers/reject/";

    let data = JSON.stringify({ uuid: uuid, status_description: status_description });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async exchangesList(filters = {}) {
    let path = "/api/currencies/exchanges/?" + Qs.stringify(filters, { arrayFormat: "comma" });

    let response = await this.client.get(path, {
      headers: await this._getHeaders(path),
    });

    return response;
  }

  async exchangesCreate(holder_id, exchange_rule, from_unit, to_unit, from_amount, description, auto_reject_timeout) {
    let path = "/api/currencies/exchanges/create/";

    let data = JSON.stringify({
      holder_id: holder_id,
      exchange_rule: exchange_rule,
      from_unit: from_unit,
      to_unit: to_unit,
      from_amount: from_amount,
      description: description,
      auto_reject_timeout: auto_reject_timeout,
    });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async exchangesConfirm(uuid, status_description) {
    let path = "/api/currencies/exchanges/confirm/";

    let data = JSON.stringify({ uuid: uuid, status_description: status_description });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }

  async exchangesReject(uuid, status_description) {
    let path = "/api/currencies/exchanges/reject/";

    let data = JSON.stringify({ uuid: uuid, status_description: status_description });

    let response = await this.client.post(path, data, {
      headers: await this._getHeaders(path, data),
    });

    return response;
  }
}
