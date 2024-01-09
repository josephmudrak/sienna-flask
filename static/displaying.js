const elSocket = io.connect(
    "http://localhost:3000/stream"
);

// Logging
elSocket.on("connect", () => {
    console.log("WebSocket connection opened")
})

elSocket.on("message", async (data) => {
    console.log(data)
    if (data === "new_response") {
        document.getElementById("conversation").innerHTML += "<br><br>"
        return;
    }
    await new Promise(resolve => setTimeout(resolve, 2000));
    document.getElementById("conversation").innerHTML += `<span style="color:red">${data}</span>`;
});

elSocket.on("disconnect", () => {
    console.log("WebSocket connection closed")
});
