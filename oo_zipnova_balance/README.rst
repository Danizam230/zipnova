=======================
Zipnova Account Balance
=======================

Description
===========

Read-only screen "Saldo de cuenta Zipnova" under Purchase > Reporting. It
queries ``GET /v2/accounts/{id}/billing`` of the Zipnova API and shows the
current balance (debt), credit limit and currency, available credit and the
last update. It never creates vendor bills or purchase orders.

Configuration
=============

* Zipnova credentials (Account ID, API Token, API Secret) are the ones of the
  ``zipnova`` module, on the company. No extra credentials are needed.
* System parameter ``zipnova_balance.web_url`` (default
  ``https://app.zipnova.com.ar``) is the Zipnova web platform URL.
* Optional scheduled action "Zipnova: refresh account balances" (every 6
  hours, inactive by default).

Usage
=====

Open Purchase > Reporting > Zipnova Account Balance. The balance of the
current company is refreshed on open; use "Refresh Balance" to update it and
"Go to Zipnova" to pay on the Zipnova platform. API errors are shown on the
screen instead of blocking it.

Credits
=======

Authors
-------

* OnlyOne

Maintainers
-----------

This module is maintained by `OnlyOne <https://www.onlyone.com.ar>`_.
