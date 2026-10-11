document.documentElement.classList.add("js");

const menuToggle = document.querySelector(".menu-toggle");
const siteNav = document.querySelector("#site-nav");
const heroGrid = document.querySelector(".hero-grid");
const statusMessage = document.querySelector("[data-status-message]");
const statusMessages = [
  "Security level: probably fine.",
  "Plan A failed. Deploying Plan C.",
  "One keyboard. Zero adult supervision.",
  "The coffee is now a critical system dependency."
];
const challengeForm = document.querySelector(".challenge-form");
const challengeInput = document.querySelector("#vault-code-input");
const challengeStatus = document.querySelector(".challenge-status");
const challengeReset = document.querySelector(".challenge-reset");
const challengeSuccess = document.querySelector(".challenge-success");
const eventAccess = document.querySelector("[data-event-access]");
const registrationTriggers = document.querySelectorAll("[data-registration-trigger]");
const vaultCode = "264";
let challengeAttempts = 0;
const operationIntro = document.querySelector("[data-operation-intro]");
const introSkip = document.querySelector("[data-intro-skip]");

if (menuToggle && siteNav) {
  menuToggle.addEventListener("click", () => {
    const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!isOpen));
    siteNav.classList.toggle("is-open", !isOpen);
  });

  siteNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuToggle.setAttribute("aria-expanded", "false");
      siteNav.classList.remove("is-open");
    });
  });
}

if (heroGrid && window.matchMedia("(pointer: fine)").matches) {
  heroGrid.addEventListener("pointermove", (event) => {
    const bounds = heroGrid.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
    heroGrid.style.setProperty("--pointer-x", `${x * 14}px`);
    heroGrid.style.setProperty("--pointer-y", `${y * 10}px`);
  });

  heroGrid.addEventListener("pointerleave", () => {
    heroGrid.style.setProperty("--pointer-x", "0px");
    heroGrid.style.setProperty("--pointer-y", "0px");
  });
}

if (statusMessage && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  let statusIndex = 0;
  window.setInterval(() => {
    statusIndex = (statusIndex + 1) % statusMessages.length;
    statusMessage.classList.add("is-changing");
    window.setTimeout(() => {
      statusMessage.textContent = statusMessages[statusIndex];
      statusMessage.classList.remove("is-changing");
    }, 180);
  }, 3200);
}

if (operationIntro && introSkip) {
  const introSeen = sessionStorage.getItem("hackheist-operation-intro");
  const reducedIntro = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const closeIntro = () => {
    operationIntro.classList.add("is-dismissed");
    operationIntro.setAttribute("aria-hidden", "true");
    sessionStorage.setItem("hackheist-operation-intro", "seen");
  };

  if (introSeen || reducedIntro) {
    closeIntro();
  } else {
    operationIntro.removeAttribute("aria-hidden");
    window.setTimeout(closeIntro, 1800);
    introSkip.addEventListener("click", closeIntro, { once: true });
  }
}

if (challengeForm && challengeInput && challengeStatus && challengeReset) {
  const resetChallenge = () => {
    challengeAttempts = 0;
    challengeInput.value = "";
    challengeInput.disabled = false;
    challengeForm.querySelector("button").disabled = false;
    challengeStatus.className = "challenge-status";
    challengeStatus.textContent = "Three attempts. No pressure.";
    challengeSuccess.hidden = true;
    challengeForm.classList.remove("is-unlocked");
    challengeReset.hidden = true;
  };

  challengeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (challengeAttempts >= 3) return;
    challengeAttempts += 1;

    if (challengeInput.value === vaultCode) {
      challengeStatus.className = "challenge-status is-success";
      challengeStatus.textContent = "VAULT CRACKED — MISSION ACCEPTED.";
      challengeSuccess.hidden = false;
      challengeForm.classList.add("is-unlocked");
      challengeInput.disabled = true;
      challengeForm.querySelector("button").disabled = true;
      challengeReset.hidden = false;
      return;
    }

    const remaining = 3 - challengeAttempts;
    challengeStatus.className = "challenge-status is-failure";
    challengeStatus.textContent = remaining
      ? `ACCESS DENIED. ${remaining} attempt${remaining === 1 ? "" : "s"} remaining.`
      : "ACCESS DENIED. The vault is taking a coffee break.";
    if (!remaining) {
      challengeInput.disabled = true;
      challengeForm.querySelector("button").disabled = true;
      challengeReset.hidden = false;
    }
  });

  challengeReset.addEventListener("click", resetChallenge);
}

const revealElements = document.querySelectorAll(".reveal");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if ("IntersectionObserver" in window && !reducedMotion) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  revealElements.forEach((element) => revealObserver.observe(element));
} else {
  revealElements.forEach((element) => element.classList.add("is-visible"));
}

const sections = document.querySelectorAll("main > section");
const navLinks = document.querySelectorAll(".site-nav a[href^='#']");
const progressSteps = document.querySelectorAll("[data-progress-step]");

if ("IntersectionObserver" in window) {
  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${entry.target.id}`);
      });
    });
  }, { rootMargin: "-25% 0px -65% 0px" });

  sections.forEach((section) => sectionObserver.observe(section));
}

if ("IntersectionObserver" in window && progressSteps.length) {
  const progressObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const progressId = entry.target.id === "cta" ? "details" : entry.target.id;
      progressSteps.forEach((step) => {
        step.classList.toggle("is-current", step.dataset.progressStep === progressId);
      });
    });
  }, { rootMargin: "-35% 0px -55% 0px" });
  sections.forEach((section) => progressObserver.observe(section));
}

if (eventAccess) {
  const updateRegistrationTriggers = (registrationOpen) => {
    registrationTriggers.forEach((trigger) => {
      trigger.disabled = !registrationOpen;
      trigger.setAttribute("aria-disabled", String(!registrationOpen));
      trigger.classList.toggle("button-disabled", !registrationOpen);
      trigger.innerHTML = registrationOpen
        ? "Register Now"
        : "Register Now <span>/ Opening Soon</span>";
    });
  };

  registrationTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      eventAccess.scrollIntoView({behavior: "smooth", block: "center"});
      window.setTimeout(() => {
        eventAccess.querySelector("input")?.focus();
      }, 350);
    });
  });

  const renderMessage = (message, type = "status") => {
    eventAccess.querySelector("[role=status], [role=alert]")?.remove();
    const element = document.createElement("p");
    element.setAttribute("role", type);
    element.textContent = message;
    eventAccess.append(element);
  };

  const field = (label, name, type = "text") => {
    const wrapper = document.createElement("label");
    wrapper.textContent = label;
    const input = document.createElement("input");
    input.name = name;
    input.type = type;
    input.required = true;
    if (type === "email") input.autocomplete = "email";
    wrapper.append(input);
    return wrapper;
  };

  const postJson = async (url, csrfToken, payload) => {
    const response = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRF-Token": csrfToken},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The operation could not be completed.");
    return data;
  };

  const submitWithLoading = async (form, action) => {
    const submit = form.querySelector("button[type=submit]");
    const originalLabel = submit.textContent;
    submit.disabled = true;
    submit.textContent = "Transmitting...";
    try {
      await action();
    } finally {
      submit.disabled = false;
      submit.textContent = originalLabel;
    }
  };

  const renderTeamTools = (csrfToken) => {
    eventAccess.innerHTML = '<p class="eyebrow">TEAM CHANNEL</p><p>Participant verified. Assemble your crew.</p>';
    const tools = document.createElement("div");
    tools.className = "team-tools";
    const createForm = document.createElement("form");
    createForm.innerHTML = '<label>Team name<input name="team_name" maxlength="80" required></label><button class="button button-secondary" type="submit">Create team</button>';
    const joinForm = document.createElement("form");
    joinForm.innerHTML = '<label>Invitation code<input name="invite_code" maxlength="12" required></label><button class="button button-secondary" type="submit">Join team</button>';
    tools.append(createForm, joinForm);
    eventAccess.append(tools);

    createForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      await submitWithLoading(createForm, async () => {
        try {
          const data = await postJson("/api/teams/create", csrfToken, {
            team_name: new FormData(createForm).get("team_name")
          });
          renderMessage(data.message);
        } catch (error) {
          renderMessage(error.message, "alert");
        }
      });
    });
    joinForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      await submitWithLoading(joinForm, async () => {
        try {
          const data = await postJson("/api/teams/join", csrfToken, {
            invite_code: new FormData(joinForm).get("invite_code")
          });
          renderMessage(data.message);
        } catch (error) {
          renderMessage(error.message, "alert");
        }
      });
    });
  };

  const loadEventAccess = async () => {
    try {
      const response = await fetch("/api/state", {headers: {"Accept": "application/json"}});
      if (!response.ok) return;
      const state = await response.json();
      updateRegistrationTriggers(state.registration_open === true);
      if (!state.registration_open) return;
      if (state.participant) {
        renderTeamTools(state.csrf_token);
        return;
      }
      eventAccess.innerHTML = '<p class="eyebrow">REGISTRATION CHANNEL</p><p>Register to receive access to team operations.</p>';
      const form = document.createElement("form");
      const row = document.createElement("div");
      row.className = "form-row";
      row.append(field("Name", "name"), field("Email", "email", "email"));
      form.append(row);
      const submit = document.createElement("button");
      submit.className = "button button-secondary";
      submit.type = "submit";
      submit.textContent = "Register";
      form.append(submit);
      eventAccess.append(form);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const values = new FormData(form);
        await submitWithLoading(form, async () => {
          try {
            const data = await postJson("/api/register", state.csrf_token, {
              name: values.get("name"),
              email: values.get("email")
            });
            renderTeamTools(state.csrf_token);
            renderMessage(data.message);
          } catch (error) {
            renderMessage(error.message, "alert");
          }
        });
      });
    } catch {
      // A static preview should retain the honest closed-registration state.
    }
  };

  loadEventAccess();
}
