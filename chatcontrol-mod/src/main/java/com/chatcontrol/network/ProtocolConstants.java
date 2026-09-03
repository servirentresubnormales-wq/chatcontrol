package com.chatcontrol.network;

public final class ProtocolConstants {

    private ProtocolConstants() {}

    public static final int PROTOCOL_VERSION = 1;
    public static final String PROTOCOL_VERSION_STRING = "1.0";
    public static final int MAX_MESSAGE_SIZE = 8192;
    public static final long DEFAULT_TIMEOUT_MS = 5000;
}
