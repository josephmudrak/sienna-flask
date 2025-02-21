let locale;

let translations = {};

async function fetchTranslationsFor(newLocale) {
  const response = await fetch(`/static/lang/${newLocale}.json`);
  return await response.json();
}

// Replace inner text with corresponding translation
function translateElement(element) {
  const key = element.getAttribute("data-i18n-key");
  const translation = translations[key];
  element.innerText = translation;
}

// Replace each element with corresponding translation
function translatePage() {
  document.querySelectorAll("[data-i18n-key]").forEach(translateElement);
}

async function notifyBackend(newLocale) {
  await fetch("/set-locale", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ locale: newLocale }),
  });
}

// Load translations and translate page to given locale
async function setLocale(newLocale) {
  if (newLocale === locale) return;

  await notifyBackend(newLocale);

  const newTranslations = await fetchTranslationsFor(newLocale);
  locale = newLocale;
  translations = newTranslations;
  translatePage();
}

// Load locale translations and update page
function bindLocaleSwitcher(initialValue) {
  const switcher = document.querySelector("[data-i18n-switcher]");
  switcher.value = initialValue;
  switcher.onchange = (e) => {
    // Set locale to selected option
    setLocale(e.target.value);
  };
}

export function t(key, placeholders = {}) {
  let translation = translations[key] || key; // Fallback if no translation

  // Replace placeholders
  Object.keys(placeholders).forEach((placeholder) => {
    const value = placeholders[placeholder];
    translation = translation.replace(`{${placeholder}}`, value);
  });

  return translation;
}

function startRecording(el, rec) {
  el.innerHTML = t("recording");
  el.disabled = true;

  // Initialise connection to Deepgram
  const dgSocket = new WebSocket(
    "wss://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&interim_results=true",
    ["token", "a12a55ee5b9e4bb5ed14bcbf6f8af42acfa0c63d"]
  );

  // Logging WebSocket events
  dgSocket.onopen = () => {
    // Send data to Deepgram in increments
    rec.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0 && dgSocket.readyState == 1) {
        dgSocket.send(event.data);
      }
    });

    rec.start(150);
  };

  dgSocket.onmessage = async (msg) => {
    // Parse data sent from Deepgram
    const dgReceived = JSON.parse(msg.data);
    const dgTranscript = dgReceived.channel.alternatives[0].transcript;

    if (dgTranscript && dgReceived.is_final) {
      document.getElementById(
        "conversation"
      ).innerHTML += `<br><br><span class="human">${dgTranscript}</span>`;
      window.scrollTo(0, document.body.scrollHeight);
      console.log(dgTranscript);
      rec.stop();
      dgSocket.close();

      // Send to GPT-4 & ElevenLabs
      await fetch("/reply", { method: "POST", body: dgTranscript });

      dgSocket.close();
      el.innerHTML = t("start_recording");
      el.disabled = false;
    }
  };

  dgSocket.onerror = (err) => {
    console.log({ event: "onerror", err });
  };
}

document.addEventListener("DOMContentLoaded", async () => {
  setLocale(defaultLocale);
  bindLocaleSwitcher(defaultLocale);

  const btnStart = document.getElementById("recStart");

  navigator.mediaDevices
    .getUserMedia({ audio: true })
    .then((stream) => {
      const mediaRecorder = new MediaRecorder(stream);

      btnStart.addEventListener(
        "click",
        startRecording(btnStart, mediaRecorder)
      );

      // Trigger recording on space press
      document.addEventListener("keyup", (e) => {
        if (e.code === "Space") {
          startRecording(btnStart, mediaRecorder);
        }
      });
    })
    .catch((err) => console.error(t("error_accessing_microphone"), err));
});
