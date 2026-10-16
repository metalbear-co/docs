---
title: Single Sign-On
description: Let your team sign in to the cloud dashboard through your identity provider
tags:
  - alpha
  - enterprise
---

# Single Sign-On

The cloud dashboard at [app.metalbear.com](https://app.metalbear.com) supports SAML single sign-on, so your team can sign in through your identity provider instead of a password or Google account. Once a connection is on, anyone whose email is under your claimed domain is sent to your identity provider at sign-in, and access is granted or removed from there.

Single sign-on is available on the Enterprise plan. It applies to the cloud dashboard only; the [license server dashboard](license-server.md) is in-cluster and uses your cluster's own access control.

{% hint style="info" %}
Setup walks you through a guide for Okta, Microsoft Entra ID (Azure AD), Google, OneLogin, Ping Identity, JumpCloud, or Rippling. Any other SAML 2.0 provider works with the Custom SAML guide.
{% endhint %}

## Before you start

* You need to be an admin of your organization on app.metalbear.com.
* You need admin access to your identity provider to create a SAML application.
* You need to be able to add a DNS TXT record for your email domain.

## Set up a connection

1. Sign in at [app.metalbear.com](https://app.metalbear.com) and go to **Settings** → **Team** → **Manage members**.
2. In the portal that opens, choose **SSO** in the sidebar, then **Setup SSO connection**.
3. Pick your identity provider. The guide shows the values to paste into the SAML application on your provider's side:

   | Field in your identity provider | Value |
   | --- | --- |
   | Single sign-on URL (ACS URL) | `https://identity.metalbear.com/auth/saml/callback` |
   | Audience URI (SP Entity ID) | `https://identity.metalbear.com` |
   | Name ID format | `EmailAddress` |

   Assign the users or groups who should have access to the application in your identity provider.

4. Back in the setup wizard, submit your identity provider's metadata: paste the metadata URL, or upload the metadata XML, that your provider gives you for the application.
5. **Claim your domain**: enter your email domain and add the DNS TXT record the wizard shows. Validation runs once the record is live, which can take a few minutes depending on your DNS provider.
6. **Manage authorization**: choose the role that users signing in through this connection get. Start with a non-admin role; you can promote individual users afterwards under **Users**.
7. Turn the connection's **Status** on.

To check it works, open [app.metalbear.com](https://app.metalbear.com) in a private window, enter an email under the claimed domain and press **Continue**. You should be redirected to your identity provider and land back on the dashboard signed in.

## How sign-in works afterwards

* Sign-in is email-first. An email under a claimed domain is redirected to your identity provider; other emails see the usual password and Google options.
* A user who signs in through SSO for the first time is created in your organization with the connection's role. Existing members keep their current role.
* Removing a user from the application in your identity provider stops them signing in. To remove them from your organization as well, delete them under **Users** in the same portal.

## Troubleshooting

* **"SAML Response is not valid for this audience"**: the Audience URI in your identity provider does not match `https://identity.metalbear.com` exactly. Check for a trailing slash or whitespace.
* **Sign-in still shows the password form**: the domain is not validated yet, or the connection's Status is off. Open **SSO** in the portal and check both.
* **User lands on an error after the identity provider**: the user is not assigned to the application on the identity provider's side, or the Name ID is not their email address.

If you get stuck, [contact us](https://metalbear.com/mirrord/contact/) with your identity provider and the error text.
