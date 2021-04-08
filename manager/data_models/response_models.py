from uuid import UUID

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ServiceResponse(BaseModel):
    name: str
    version: str
    image: str
    main: bool


class TokenResponse(BaseModel):
    Token: str
    Id: UUID


class HealthResponse(BaseModel):
    Status: str
    FailingStreak: int
    Log: List[dict]


class StateResponse(BaseModel):
    Status: str
    Running: bool
    Paused: bool
    Restarting: bool
    OOMKilled: bool
    Dead: bool
    Pid: int
    ExitCode: int
    Error: str
    StartedAt: str
    FinishedAt: str
    Health: Optional[HealthResponse]


class NetworkSettingsResponse(BaseModel):
    Bridge: str
    SandboxID: str
    HairpinMode: bool
    LinkLocalIPv6Address: str
    LinkLocalIPv6PrefixLen: int
    Ports: dict
    SandboxKey: str
    SecondaryIPAddresses: Optional[str]
    SecondaryIPv6Addresses: Optional[str]
    EndpointID: str
    Gateway: str
    GlobalIPv6Address: str
    GlobalIPv6PrefixLen: int
    IPAddress: str
    IPPrefixLen: int
    IPv6Gateway: str
    MacAddress: str
    Networks: Dict[str, Dict]


class InspectResponse(BaseModel):
    Id: str
    Created: str
    ContainerPath: str = Field(..., alias="Path")
    Args: List[str]
    State: StateResponse
    Image: str
    ResolvConfPath: str
    HostnamePath: str
    HostsPath: str
    LogPath: str
    Name: str
    RestartCount: int
    Driver: str
    Platform: str
    MountLabel: str
    ProcessLabel: str
    AppArmorProfile: str
    ExecIDs: Optional[List[str]]
    HostConfig: dict
    GraphDriver: dict
    Mounts: list
    Configuration: dict = Field(..., alias="Config")
    NetworkSettings: NetworkSettingsResponse
