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
    Health: Optional[HealthResponse] = None


class NetworkSettingsResponse(BaseModel):
    # Docker Engine 29+ no longer populates the legacy top-level network
    # fields (Bridge, IPAddress, MacAddress, etc.) for containers attached
    # only to a custom network; that data now lives under `Networks`. Keep
    # them optional so inspection doesn't fail response validation.
    SandboxID: str
    Ports: dict
    SandboxKey: str
    Networks: Dict[str, Dict]
    Bridge: Optional[str] = None
    HairpinMode: Optional[bool] = None
    LinkLocalIPv6Address: Optional[str] = None
    LinkLocalIPv6PrefixLen: Optional[int] = None
    SecondaryIPAddresses: Optional[str] = None
    SecondaryIPv6Addresses: Optional[str] = None
    EndpointID: Optional[str] = None
    Gateway: Optional[str] = None
    GlobalIPv6Address: Optional[str] = None
    GlobalIPv6PrefixLen: Optional[int] = None
    IPAddress: Optional[str] = None
    IPPrefixLen: Optional[int] = None
    IPv6Gateway: Optional[str] = None
    MacAddress: Optional[str] = None


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
    ExecIDs: Optional[List[str]] = None
    HostConfig: dict
    # Docker 29+ with the containerd/overlayfs image store returns `Storage`
    # (and `ImageManifestDescriptor`) instead of the legacy `GraphDriver`, so
    # none of these can be required for inspection to work across drivers.
    GraphDriver: Optional[dict] = None
    Storage: Optional[dict] = None
    ImageManifestDescriptor: Optional[dict] = None
    Mounts: list
    Configuration: dict = Field(..., alias="Config")
    NetworkSettings: NetworkSettingsResponse
