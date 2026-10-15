document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginDialog = document.getElementById("teacher-login-dialog");
  const loginForm = document.getElementById("teacher-login-form");
  const loginError = document.getElementById("teacher-login-error");
  const loginButton = document.getElementById("teacher-login-button");
  const logoutButton = document.getElementById("teacher-logout-button");
  const teacherStatus = document.getElementById("teacher-status");
  const loginPrompt = document.getElementById("teacher-login-prompt");
  let accessToken = null;

  function updateTeacherControls(username = "") {
    const isTeacher = Boolean(accessToken);
    teacherStatus.textContent = isTeacher ? `Signed in as ${username}` : "Student view";
    loginButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    loginPrompt.classList.toggle("hidden", isTeacher);
    signupForm.classList.toggle("hidden", !isTeacher);
  }

  function showMessage(message, className) {
    messageDiv.textContent = message;
    messageDiv.className = className;
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function handleUnauthorized() {
    accessToken = null;
    updateTeacherControls();
    showMessage("Your teacher session expired. Please sign in again.", "error");
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(activitySelect.options[0]);

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${accessToken ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Unregister ${email}">Remove</button>` : ""}</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        if (response.status === 401) {
          handleUnauthorized();
        } else {
          showMessage(result.detail || "An error occurred", "error");
        }
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        if (response.status === 401) {
          handleUnauthorized();
        } else {
          showMessage(result.detail || "An error occurred", "error");
        }
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginButton.addEventListener("click", () => {
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("teacher-login-cancel").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");
    const username = document.getElementById("teacher-username").value;
    const password = document.getElementById("teacher-password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        loginError.textContent = result.detail || "Unable to sign in.";
        loginError.classList.remove("hidden");
        return;
      }

      accessToken = result.access_token;
      updateTeacherControls(result.username);
      loginForm.reset();
      loginDialog.close();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Unable to sign in. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Teacher login failed:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    const token = accessToken;
    accessToken = null;
    updateTeacherControls();
    try {
      await fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (error) {
      console.error("Teacher logout failed:", error);
    } finally {
      fetchActivities();
    }
  });

  // Initialize app
  updateTeacherControls();
  fetchActivities();
});
