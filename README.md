# birthday-telegram-bot

This bot is for remembering your birthdays and reminding you about them via Telegram. Uses [birthday-api](https://github.com/orehzzz/birthday-api).

## `flake.nix`

### Dev shell

To enter development shell, run `nix develop`.
It will provide you with `python310`, `uv`, and an executable `birthday-bot`.

### Deploy

1. Add the project to your flake's inputs:

```nix
inputs = {
  birthday-bot-app = { url = "github:orehzzz/birthday-telegram-bot"; };
};
```

2. Import the NixOS module:

```nix
imports = [ inputs.birthday-bot-app.nixosModules.default ];
```

3. Enable the service:

```nix
services.birthday-bot = {
    enable = true;
};
```
