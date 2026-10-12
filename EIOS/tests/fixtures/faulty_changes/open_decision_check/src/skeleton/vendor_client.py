"""Overlay module: imports a vendor SDK outside the providers directory."""

import skeleton_vendor_sdk


def client() -> object:
    return skeleton_vendor_sdk.Client()
