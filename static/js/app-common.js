const accessToken = localStorage.getItem("accessToken");
if (!accessToken) {
  location.replace("/");
}

async function fetchWithAuth(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.status === 401) {
    localStorage.removeItem("accessToken");
    location.replace("/");
    throw new Error("Session expired");
  }

  return response;
}

const logoutButton = document.getElementById("logout");
if (logoutButton) {
  logoutButton.addEventListener("click", () => {
    localStorage.removeItem("accessToken");
    location.replace("/");
  });
}
