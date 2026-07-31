"""Configuration gate for a future Apple Push Notification delivery adapter."""
from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class ApplePushConfiguration:
    team_id: str | None
    key_id: str | None
    key_path: str | None
    bundle_id: str | None
    device_token: str | None

    @property
    def missing(self) -> list[str]:
        values = {
            "APPLE_TEAM_ID": self.team_id,
            "APPLE_KEY_ID": self.key_id,
            "APPLE_PUSH_KEY_PATH": self.key_path,
            "IRON_MAN_IOS_BUNDLE_ID": self.bundle_id,
            "IRON_MAN_DEVICE_TOKEN": self.device_token,
        }
        return [name for name, value in values.items() if not value]

    @property
    def configured(self) -> bool:
        return not self.missing


class PhonePushGateway:
    """Does not send until all Apple-issued credentials are explicitly supplied."""

    @staticmethod
    def configuration_from_environment() -> ApplePushConfiguration:
        return ApplePushConfiguration(
            getenv("APPLE_TEAM_ID"),
            getenv("APPLE_KEY_ID"),
            getenv("APPLE_PUSH_KEY_PATH"),
            getenv("IRON_MAN_IOS_BUNDLE_ID"),
            getenv("IRON_MAN_DEVICE_TOKEN"),
        )

    def readiness(self) -> dict[str, object]:
        configuration = self.configuration_from_environment()
        return {
            "ready": configuration.configured,
            "missing": configuration.missing,
            "status": "ready_for_apns_delivery" if configuration.configured else "needs_apple_configuration",
        }


phone_push_gateway = PhonePushGateway()
