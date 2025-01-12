#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import logging
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Generic, List, Mapping, Optional, Set, TypeVar

from pydantic import BaseModel, Field, root_validator, validator
from pydantic.generics import GenericModel

config_path: str = Field(default="secrets/config.json", description="Path to a JSON object representing a valid connector configuration")
invalid_config_path: str = Field(description="Path to a JSON object representing an invalid connector configuration")
spec_path: str = Field(
    default="secrets/spec.json", description="Path to a JSON object representing the spec expected to be output by this connector"
)
configured_catalog_path: Optional[str] = Field(default=None, description="Path to configured catalog")
timeout_seconds: int = Field(default=None, description="Test execution timeout_seconds", ge=0)

SEMVER_REGEX = r"(0|(?:[1-9]\d*))(?:\.(0|(?:[1-9]\d*))(?:\.(0|(?:[1-9]\d*)))?(?:\-([\w][\w\.\-_]*))?)?"
ALLOW_LEGACY_CONFIG = True


class BaseConfig(BaseModel):
    class Config:
        extra = "forbid"


TestConfigT = TypeVar("TestConfigT")


class BackwardCompatibilityTestsConfig(BaseConfig):
    previous_connector_version: str = Field(
        regex=SEMVER_REGEX, default="latest", description="Previous connector version to use for backward compatibility tests."
    )
    disable_for_version: Optional[str] = Field(
        regex=SEMVER_REGEX, default=None, description="Disable backward compatibility tests for a specific connector version."
    )


class SpecTestConfig(BaseConfig):
    spec_path: str = spec_path
    config_path: str = config_path
    timeout_seconds: int = timeout_seconds
    backward_compatibility_tests_config: BackwardCompatibilityTestsConfig = Field(
        description="Configuration for the backward compatibility tests.", default=BackwardCompatibilityTestsConfig()
    )


class ConnectionTestConfig(BaseConfig):
    class Status(Enum):
        Succeed = "succeed"
        Failed = "failed"
        Exception = "exception"

    config_path: str = config_path
    status: Status = Field(Status.Succeed, description="Indicate if connection check should succeed with provided config")
    timeout_seconds: int = timeout_seconds


class DiscoveryTestConfig(BaseConfig):
    config_path: str = config_path
    timeout_seconds: int = timeout_seconds
    backward_compatibility_tests_config: BackwardCompatibilityTestsConfig = Field(
        description="Configuration for the backward compatibility tests.", default=BackwardCompatibilityTestsConfig()
    )


class ExpectedRecordsConfig(BaseModel):
    class Config:
        extra = "forbid"

    path: Path = Field(description="File with expected records")
    extra_fields: bool = Field(False, description="Allow records to have other fields")
    exact_order: bool = Field(False, description="Ensure that records produced in exact same order")
    extra_records: bool = Field(
        True, description="Allow connector to produce extra records, but still enforce all records from the expected file to be produced"
    )

    @validator("exact_order", always=True)
    def validate_exact_order(cls, exact_order, values):
        if "extra_fields" in values and values["extra_fields"] and not exact_order:
            raise ValueError("exact_order must be on if extra_fields enabled")
        return exact_order

    @validator("extra_records", always=True)
    def validate_extra_records(cls, extra_records, values):
        if "extra_fields" in values and values["extra_fields"] and extra_records:
            raise ValueError("extra_records must be off if extra_fields enabled")
        return extra_records


class BasicReadTestConfig(BaseConfig):
    config_path: str = config_path
    configured_catalog_path: Optional[str] = configured_catalog_path
    empty_streams: Set[str] = Field(default_factory=set, description="We validate that all streams has records. These are exceptions")
    expect_records: Optional[ExpectedRecordsConfig] = Field(description="Expected records from the read")
    validate_schema: bool = Field(True, description="Ensure that records match the schema of the corresponding stream")
    # TODO: remove this field after https://github.com/airbytehq/airbyte/issues/8312 is done
    validate_data_points: bool = Field(
        False, description="Set whether we need to validate that all fields in all streams contained at least one data point"
    )
    expect_trace_message_on_failure: bool = Field(True, description="Ensure that a trace message is emitted when the connector crashes")
    timeout_seconds: int = timeout_seconds


class FullRefreshConfig(BaseConfig):
    """Full refresh test config

    Attributes:
        ignored_fields for each stream, list of fields path. Path should be in format "object_key/object_key2"
    """

    config_path: str = config_path
    configured_catalog_path: Optional[str] = configured_catalog_path
    timeout_seconds: int = timeout_seconds
    ignored_fields: Optional[Mapping[str, List[str]]] = Field(
        description="For each stream, list of fields path ignoring in sequential reads test"
    )


class IncrementalConfig(BaseConfig):
    config_path: str = config_path
    configured_catalog_path: Optional[str] = configured_catalog_path
    cursor_paths: Optional[Mapping[str, List[str]]] = Field(
        description="For each stream, the path of its cursor field in the output state messages."
    )
    future_state_path: Optional[str] = Field(description="Path to a state file with values in far future")
    timeout_seconds: int = timeout_seconds
    threshold_days: int = Field(
        description="Allow records to be emitted with a cursor value this number of days before the state cursor",
        default=0,
        ge=0,
    )
    skip_comprehensive_incremental_tests: Optional[bool] = Field(
        description="Determines whether to skip more granular testing for incremental syncs", default=False
    )


class GenericTestConfig(GenericModel, Generic[TestConfigT]):
    bypass_reason: Optional[str]
    tests: Optional[List[TestConfigT]]

    @validator("tests", always=True)
    def no_bypass_reason_when_tests_is_set(cls, tests, values):
        if tests and values.get("bypass_reason"):
            raise ValueError("You can't set a bypass_reason if tests are set.")
        return tests


class AcceptanceTestConfigurations(BaseConfig):
    spec: Optional[GenericTestConfig[SpecTestConfig]]
    connection: Optional[GenericTestConfig[ConnectionTestConfig]]
    discovery: Optional[GenericTestConfig[DiscoveryTestConfig]]
    basic_read: Optional[GenericTestConfig[BasicReadTestConfig]]
    full_refresh: Optional[GenericTestConfig[FullRefreshConfig]]
    incremental: Optional[GenericTestConfig[IncrementalConfig]]


class Config(BaseConfig):
    class TestStrictnessLevel(str, Enum):
        high = "high"
        low = "low"

    connector_image: str = Field(description="Docker image to test, for example 'airbyte/source-hubspot:dev'")
    acceptance_tests: AcceptanceTestConfigurations = Field(description="List of the acceptance test to run with their configs")
    base_path: Optional[str] = Field(description="Base path for all relative paths")
    test_strictness_level: Optional[TestStrictnessLevel] = Field(
        default=TestStrictnessLevel.low,
        description="Corresponds to a strictness level of the test suite and will change which tests are mandatory for a successful run.",
    )

    @staticmethod
    def is_legacy(config: dict) -> bool:
        """Check if a configuration is 'legacy'.
        We consider it is legacy if a 'tests' field exists at its root level (prior to v0.2.12).

        Args:
            config (dict): A configuration

        Returns:
            bool: Whether the configuration is legacy.
        """
        return "tests" in config

    @staticmethod
    def migrate_legacy_to_current_config(legacy_config: dict) -> dict:
        """Convert configuration structure created prior to v0.2.12 into the current structure.
        e.g.
        This structure:
            {"connector_image": "my-connector-image", "tests": {"spec": [{"spec_path": "my/spec/path.json"}]}
        Gets converted to:
            {"connector_image": "my-connector-image", "acceptance_tests": {"spec": {"tests": [{"spec_path": "my/spec/path.json"}]}}

        Args:
            legacy_config (dict): A legacy configuration

        Returns:
            dict: A migrated configuration
        """
        migrated_config = deepcopy(legacy_config)
        migrated_config.pop("tests")
        migrated_config["acceptance_tests"] = {}
        for test_name, test_configs in legacy_config["tests"].items():
            migrated_config["acceptance_tests"][test_name] = {"tests": test_configs}
        return migrated_config

    @root_validator(pre=True)
    def legacy_format_adapter(cls, values: dict) -> dict:
        """Root level validator executed 'pre' field validation to migrate a legacy config to the current structure.

        Args:
            values (dict): The raw configuration.

        Returns:
            dict: The migrated configuration if needed.
        """
        if ALLOW_LEGACY_CONFIG and cls.is_legacy(values):
            logging.warn("The acceptance-test-config.yml file is in a legacy format. Please migrate to the latest format.")
            return cls.migrate_legacy_to_current_config(values)
        else:
            return values
