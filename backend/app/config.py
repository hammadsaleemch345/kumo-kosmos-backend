from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    session_ttl_hours: int = 720
    password_reset_ttl_minutes: int = 30

    # Pending the client's actual CCBill merchant account details (open item in context.md).
    # Left optional so the app runs without them; checkout/webhook code fails loudly and early
    # if used before they're set, rather than silently misbehaving.
    ccbill_client_account: str | None = None
    ccbill_client_subaccount: str | None = None
    ccbill_dynamic_pricing_salt: str | None = None
    ccbill_webhook_secret: str | None = None


settings = Settings()
