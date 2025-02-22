import { t } from "./audio.js";

const elSocket = io.connect("http://localhost:3000/stream");

// Logging
elSocket.on("connect", () => {
  console.log(t("websocket_connection_opened"));
});

elSocket.on("message", async (data) => {
  console.log(data);
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
