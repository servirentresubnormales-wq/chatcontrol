export const API_URL = import.meta.env.PUBLIC_API_URL || "";
export const IS_CONFIGURED = API_URL !== "" && !API_URL.includes("localhost");
