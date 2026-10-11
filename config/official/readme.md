All entrypoints read this directory as `config/official`; Compose mounts it
at `/app/config/official` for the official adapter.
Copy the relevant `../onebot/features/<feature>/config.toml.example` to
`features/<feature>/config.toml` here for independent official configuration.
Scheduled news is unsupported on the official adapter.
