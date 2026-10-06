from core.constants import PermissionCode, RoleName

DEFAULT_ROLE_PERMISSIONS: dict[str, set[PermissionCode]] = {
    RoleName.SUPERUSER: set(PermissionCode),
    RoleName.ADMIN: {
        PermissionCode.USER_READ,
        PermissionCode.USER_CREATE,
        PermissionCode.USER_UPDATE,
        PermissionCode.ROLE_READ,
        PermissionCode.AUDIT_READ,
        PermissionCode.SETTINGS_READ,
        PermissionCode.SETTINGS_UPDATE,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.CUSTOMER_WRITE,
        PermissionCode.CUSTOMER_DELETE,
        PermissionCode.VEHICLE_READ,
        PermissionCode.VEHICLE_WRITE,
        PermissionCode.VEHICLE_DELETE,
    },
    RoleName.SALES: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.CUSTOMER_WRITE,
        PermissionCode.VEHICLE_READ,
        PermissionCode.VEHICLE_WRITE,
    },
    RoleName.WORKSHOP: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
    },
    RoleName.FINANCE: {
        PermissionCode.USER_READ,
        PermissionCode.AUDIT_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
    },
    RoleName.VIEWER: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
    },
}