if (localStorage.getItem("accessToken")) {
  location.replace("/app/menu");
}

const tabs = Array.from(document.querySelectorAll(".tab"));
const forms = Array.from(document.querySelectorAll("form"));
const message = document.getElementById("message");

function setMode(targetId) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.target === targetId));
  forms.forEach((form) => form.classList.toggle("active", form.id === targetId));
  message.className = "";
  message.textContent = "";
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.target));
});

document.getElementById("signin-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  message.className = "";
  message.textContent = "";

  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))),
  });
  const data = await response.json();
  if (!response.ok) {
    message.className = "error";
    message.textContent = data.detail || "Unable to sign in.";
    return;
  }

  localStorage.setItem("accessToken", data.access_token);
  location.replace("/app/menu");
});

document.getElementById("signup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  message.className = "";
  message.textContent = "";

  const response = await fetch("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))),
  });
  const data = await response.json();
  if (!response.ok) {
    message.className = "error";
    message.textContent = data.detail || "Unable to create account.";
    return;
  }

  event.currentTarget.reset();
  setMode("signin-form");
  message.className = "success";
  message.textContent = "Account created. You can sign in now.";
});
