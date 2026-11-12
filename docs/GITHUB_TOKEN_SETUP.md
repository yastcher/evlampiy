# GitHub OAuth App for the Obsidian connection

[English](#english) | [Русский](#русский) | [Español](#español) | [Deutsch](#deutsch)

---

## English

Users connect their Obsidian vault from the bot's `/obsidian` menu through GitHub's OAuth
Device Flow: the bot shows a code, the user enters it at github.com/login/device, and no
token is ever typed or pasted. The flow needs one thing from the operator: the Client ID of
a GitHub OAuth App, in `GITHUB_CLIENT_ID`.

1. On GitHub, open **Settings** → **Developer settings** → **OAuth Apps** → **New OAuth App**
   (or the same in an organization's settings).
2. Enter the name users will see on GitHub's consent page (for example `Evlampiy Notes`), a
   homepage URL, and any authorization callback URL: the device flow does not use it.
3. Register the application, tick **Enable Device Flow** on its page and save.
4. Put the **Client ID** into `.env`: `GITHUB_CLIENT_ID=<client id>`. No client secret is
   needed: the device flow does not use one.
5. Restart the bot. A user who connects grants the `repo` scope, to read and write the vault
   repository; the bot keeps that user's token in MongoDB (`github_settings`).

---

## Русский

Пользователь подключает хранилище Obsidian из меню бота `/obsidian` через OAuth Device Flow
GitHub: бот показывает код, пользователь вводит его на github.com/login/device, и токен
никто не вводит и не вставляет. От оператора нужно одно: Client ID приложения GitHub OAuth
App в `GITHUB_CLIENT_ID`.

1. На GitHub откройте **Settings** → **Developer settings** → **OAuth Apps** → **New OAuth App**
   (или то же в настройках организации).
2. Укажите имя, которое пользователи увидят на странице согласия GitHub (например
   `Evlampiy Notes`), адрес домашней страницы и любой callback URL: device flow его не использует.
3. Зарегистрируйте приложение, на его странице отметьте **Enable Device Flow** и сохраните.
4. Запишите **Client ID** в `.env`: `GITHUB_CLIENT_ID=<client id>`. Client secret не нужен:
   device flow его не использует.
5. Перезапустите бота. Подключаясь, пользователь даёт права `repo` на чтение и запись
   репозитория хранилища; бот хранит его токен в MongoDB (`github_settings`).

---

## Español

Los usuarios conectan su bóveda de Obsidian desde el menú `/obsidian` del bot mediante el
OAuth Device Flow de GitHub: el bot muestra un código, el usuario lo introduce en
github.com/login/device y nadie escribe ni pega un token. El operador solo aporta una cosa:
el Client ID de una OAuth App de GitHub, en `GITHUB_CLIENT_ID`.

1. En GitHub, abre **Settings** → **Developer settings** → **OAuth Apps** → **New OAuth App**
   (o lo mismo en la configuración de una organización).
2. Indica el nombre que verán los usuarios en la página de consentimiento de GitHub (por
   ejemplo `Evlampiy Notes`), una URL de inicio y cualquier URL de callback: el device flow
   no la usa.
3. Registra la aplicación, marca **Enable Device Flow** en su página y guarda.
4. Pon el **Client ID** en `.env`: `GITHUB_CLIENT_ID=<client id>`. No hace falta client
   secret: el device flow no lo usa.
5. Reinicia el bot. Al conectarse, el usuario concede el permiso `repo` para leer y escribir
   el repositorio de la bóveda; el bot guarda su token en MongoDB (`github_settings`).

---

## Deutsch

Benutzer verbinden ihren Obsidian-Vault über das Menü `/obsidian` des Bots mit dem OAuth
Device Flow von GitHub: Der Bot zeigt einen Code, der Benutzer gibt ihn auf
github.com/login/device ein, und niemand tippt oder fügt ein Token ein. Vom Betreiber braucht
der Ablauf nur eines: die Client ID einer GitHub OAuth App in `GITHUB_CLIENT_ID`.

1. Öffne auf GitHub **Settings** → **Developer settings** → **OAuth Apps** → **New OAuth App**
   (oder dasselbe in den Einstellungen einer Organisation).
2. Gib den Namen ein, den Benutzer auf der Zustimmungsseite von GitHub sehen (zum Beispiel
   `Evlampiy Notes`), eine Homepage-URL und eine beliebige Callback-URL: Der Device Flow
   nutzt sie nicht.
3. Registriere die Anwendung, setze auf ihrer Seite **Enable Device Flow** und speichere.
4. Trage die **Client ID** in `.env` ein: `GITHUB_CLIENT_ID=<client id>`. Ein Client Secret
   ist nicht nötig: Der Device Flow nutzt keines.
5. Starte den Bot neu. Beim Verbinden gewährt der Benutzer den Scope `repo` zum Lesen und
   Schreiben des Vault-Repositorys; der Bot speichert sein Token in MongoDB (`github_settings`).
