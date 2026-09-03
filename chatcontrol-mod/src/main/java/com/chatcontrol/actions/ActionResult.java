package com.chatcontrol.actions;

import com.chatcontrol.network.ErrorCode;

public class ActionResult {

    private final boolean success;
    private final String message;
    private final ErrorCode errorCode;

    private ActionResult(boolean success, String message, ErrorCode errorCode) {
        this.success = success;
        this.message = message;
        this.errorCode = errorCode;
    }

    public static ActionResult success(String message) {
        return new ActionResult(true, message, null);
    }

    public static ActionResult failure(String message) {
        return new ActionResult(false, message, null);
    }

    public static ActionResult failure(ErrorCode errorCode) {
        return new ActionResult(false, errorCode.getDefaultMessage(), errorCode);
    }

    public static ActionResult failure(ErrorCode errorCode, String message) {
        return new ActionResult(false, message, errorCode);
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public ErrorCode getErrorCode() {
        return errorCode;
    }

    @Override
    public String toString() {
        return (success ? "[OK] " : "[FAIL] ") + message;
    }
}
