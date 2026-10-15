const menuButton = document.querySelector(".menu-toggle");
const siteNav = document.querySelector("#site-nav");
const eventAccess = document.querySelector("[data-event-access]");
const registrationTriggers = document.querySelectorAll("[data-registration-trigger]");

// Mobile menu toggle
if (menuButton && siteNav) {
  menuButton.addEventListener("click", () => {
    const isOpen = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!isOpen));
    siteNav.classList.toggle("is-open", !isOpen);
  });

  // Close mobile navigation when a link is clicked
  siteNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuButton.setAttribute("aria-expanded", "false");
      siteNav.classList.remove("is-open");
    });
  });
}

const GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfVNx0ANEqMHLlsm-qei1T_ARVQa9C97G1bzYVMt-OGNvQSBg/viewform?usp=publish-edito";

if (eventAccess) {
  let activeGoogleFormUrl = GOOGLE_FORM_URL;

  // Update registration buttons based on server state
  const updateRegistrationButtons = (registrationOpen, formUrl) => {
    if (formUrl) activeGoogleFormUrl = formUrl;
    registrationTriggers.forEach((trigger) => {
      trigger.disabled = !registrationOpen;
      trigger.setAttribute("aria-disabled", String(!registrationOpen));
      trigger.classList.toggle("button-disabled", !registrationOpen);
      trigger.innerHTML = registrationOpen
        ? "Register Now"
        : "Register Now <span>/ Opening Soon</span>";
    });
  };

  // Open Google Form in a new tab when clicked
  registrationTriggers.forEach((button) => {
    button.addEventListener("click", () => {
      window.open(activeGoogleFormUrl, "_blank", "noopener,noreferrer");
    });
  });

  // Display Google Form registration card in the Event Details section
  const showGoogleFormAccess = (formUrl) => {
    eventAccess.innerHTML = `
      <p class="eyebrow">REGISTRATION</p>
      <p>Registration for HackHeist 2026 is officially open via Google Forms. Express your interest and register your participation below.</p>
      <div style="margin-top: 18px;">
        <a class="button button-primary" href="${formUrl}" target="_blank" rel="noopener noreferrer">
          Open Registration Form <span aria-hidden="true">↗</span>
        </a>
      </div>
    `;
  };

  // Fetch registration status from server and bind form link
  const loadRegistrationState = async () => {
    const response = await fetch("/api/state", {
      headers: {"Accept": "application/json"}
    });
    if (!response.ok) {
      throw new Error(`Registration state request failed (${response.status}).`);
    }

    const state = await response.json();
    const formUrl = state.google_form_url || GOOGLE_FORM_URL;
    updateRegistrationButtons(state.registration_open === true, formUrl);
    if (!state.registration_open) return;
    showGoogleFormAccess(formUrl);
  };

  loadRegistrationState().catch((error) => {
    console.error("Could not load registration state.", error);
  });
}
