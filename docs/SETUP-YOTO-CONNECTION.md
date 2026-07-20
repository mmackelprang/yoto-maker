# Setting up the Yoto connection

> ✅ **As of v0.1.2 the app ships with a Yoto Client ID already built in.** Most
> people need to do **nothing here** — just open the app, click **Connect my
> Yoto account**, and sign in. This document is only needed if you want to run
> the app against **your own** Yoto developer app instead of the bundled one.

Yoto Maker uploads cards to a Yoto account through Yoto's official API. Signing
in uses a **Client ID** registered at Yoto's developer dashboard. A working one
is bundled; the steps below let you register and use your own.

> **Who needs this?** Only someone who wants their own Yoto app credentials. End
> users never see any of it — they just click **Connect my Yoto account**.

---

## 1. Register an application

1. Go to **https://dashboard.yoto.dev** and sign in with your Yoto account.
2. Create a new **application** / **client**. Choose a **public client** (also
   called *native* / *PKCE* / *no client secret*). Yoto Maker uses PKCE, so **no
   client secret is needed**.
3. Give it any name, e.g. *“Yoto Maker (home)”*.

## 2. Set the redirect URL

Add this **exact** redirect/callback URL to the client's allowed redirects:

```
http://127.0.0.1:8777/yoto/callback
```

> This must match exactly. The app always runs on port **8777** on the local
> machine, which is why the port is fixed.

## 3. Enable the scopes

Enable these two scopes (permissions) for the client:

- `user:content:manage` — lets the app create/upload MYO content
- `offline_access` — lets the app stay signed in without asking every time

## 4. Copy the Client ID

Copy the **Client ID** string the dashboard shows you (it is **not** secret).

## 5. Give the Client ID to the app

Pick whichever is easiest:

**Option A — paste it into the app (no rebuild).**
Open Yoto Maker and click the **Yoto** button in the top-right corner (or
**Settings** at the bottom of the page). Under **Yoto Client ID (advanced)**,
paste your Client ID and click **Save**. It's stored on that computer only and
overrides the bundled one.

Saving a Client ID **signs you out of Yoto**, because a sign-in belongs to one
specific Client ID. The Settings page says so before you confirm, and afterwards
the **Your Yoto account** section right above tells you to sign in again. If you
change your mind, **Go back to the built-in one** appears once you've saved your
own — it signs you out too, for the same reason.

> If `YOTO_CLIENT_ID` is set on that computer (Option B), it wins over anything
> saved in the app. Settings shows **Set outside the app** in that case and
> disables the box, rather than accepting a value it would then ignore.

**Option B — environment variable.**
Set `YOTO_CLIENT_ID` to your Client ID before launching (useful for developers):

```powershell
$env:YOTO_CLIENT_ID = "your-client-id-here"
```

**Option C — bake it into a build (developers).**
Set `YOTO_CLIENT_ID` in your environment and rebuild the `.exe` (see
[DEVELOPERS.md](DEVELOPERS.md)); the app will pick it up at runtime via the same
resolution order (env → saved setting → default).

The app resolves the Client ID in this order: **`YOTO_CLIENT_ID` env var → saved
setting (Option A) → built-in default**.

---

## 6. Test it

Run the app and use the self-check (developers) or just click **Connect my Yoto
account**:

```
YotoMaker.exe --check     # prints tool + Yoto status (run from a terminal)
```

You should be able to sign in, and **Send to Yoto** should upload a card. After
uploading, open the Yoto app on a phone and tap a blank *Make Your Own* card to
link it to the new content.

---

## Notes & limitations

- **Linking a brand-new blank card** to content for the first time is done by
  tapping the card in the Yoto app — that's a Yoto step, not something any
  third-party app does for you. After the first link, updating that card's
  content is automatic.
- Yoto's API terms apply. This app is for personal/family use.
- If sign-in fails with a redirect error, double-check the redirect URL in step 2
  is exactly `http://127.0.0.1:8777/yoto/callback`.
