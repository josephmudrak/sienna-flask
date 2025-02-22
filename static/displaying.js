import { locale, t } from "./audio.js";

const elSocket = io("http://localhost:5000/stream", {
  transports: ["websocket"],
  upgrade: false,
});

// Logging
elSocket.on("connect", () => {
  elSocket.emit("set_locale", locale);
  console.log(t("websocket_connection_opened"));
});

elSocket.on("connect_error", (err) => {
  console.error(t("websocket_connection_failed"), err);
  console.log(JSON.stringify(err, null, 2));
});

elSocket.on("message", async (data) => {
  if (data === "new_response") {
    document.getElementById("conversation").innerHTML += "<br><br>";
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, 2000));
  document.getElementById(
    "conversation"
  ).innerHTML += `<span class="bot">${data}</span>`;
  window.scrollTo(0, document.body.scrollHeight);
});

elSocket.on("disconnect", () => {
  console.log(t("websocket_connection_closed"));
});
