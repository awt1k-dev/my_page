(() => {
  "use strict";

  const doc = document;
  const root = doc.documentElement;
  const header = doc.getElementById("site-header");
  const intro = doc.getElementById("intro");
  const menu = doc.getElementById("mobile-menu");
  const menuToggle = doc.querySelector(".menu-toggle");
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const narrowScreen = window.matchMedia("(max-width: 720px)").matches;

  /* Intro -------------------------------------------------- */
  const revealHero = () => {
    doc.querySelector(".hero")?.classList.add("is-ready");
  };

  const rememberIntro = () => {
    try {
      sessionStorage.setItem("awtik-intro", "1");
    } catch (_) {
      /* storage can be unavailable */
    }
  };

  const closeIntro = () => {
    if (!intro) return;
    intro.classList.add("is-done");
    rememberIntro();
    revealHero();
    window.setTimeout(() => {
      intro.hidden = true;
    }, prefersReduced ? 30 : 450);
  };

  if (root.classList.contains("no-intro") || !intro) {
    revealHero();
  } else if (prefersReduced || narrowScreen) {
    closeIntro();
  } else {
    window.setTimeout(closeIntro, 650);
  }

  /* Header theme ------------------------------------------ */
  const themedSections = [...doc.querySelectorAll("[data-header]")];

  const updateHeader = () => {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 16);

    const probe = header.offsetHeight + 8;
    let theme = doc.body.dataset.page === "index" ? "dark" : "light";

    for (const section of themedSections) {
      const top = section.offsetTop;
      if (top <= window.scrollY + probe && top + section.offsetHeight > window.scrollY + probe) {
        theme = section.dataset.header;
      }
    }

    header.classList.toggle("is-light", theme === "light");
  };

  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });
  window.addEventListener("resize", updateHeader);

  /* Mobile menu ------------------------------------------- */
  const menuLinks = menu ? [...menu.querySelectorAll("a[href]")] : [];
  const menuFocusables = menuToggle ? [menuToggle, ...menuLinks] : menuLinks;

  const setMenu = (open, { restoreFocus = true } = {}) => {
    if (!menu || !menuToggle) return;
    menuToggle.setAttribute("aria-expanded", String(open));
    menuToggle.setAttribute(
      "aria-label",
      open ? menuToggle.dataset.labelClose || "" : menuToggle.dataset.labelOpen || ""
    );
    doc.body.classList.toggle("is-locked", open);
    header?.classList.toggle("is-menu-open", open);

    if (open) {
      menu.hidden = false;
      window.requestAnimationFrame(() => {
        menu.classList.add("is-open");
        menuLinks[0]?.focus();
      });
    } else {
      menu.classList.remove("is-open");
      if (restoreFocus && (menu.contains(doc.activeElement) || doc.activeElement === menuToggle)) {
        menuToggle.focus();
      }
      window.setTimeout(() => {
        if (menuToggle.getAttribute("aria-expanded") === "false") menu.hidden = true;
      }, 280);
    }
  };

  menuToggle?.addEventListener("click", () => {
    setMenu(menuToggle.getAttribute("aria-expanded") !== "true");
  });

  menuLinks.forEach((link) => {
    link.addEventListener("click", () => setMenu(false, { restoreFocus: false }));
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 980 && menuToggle?.getAttribute("aria-expanded") === "true") {
      setMenu(false);
    }
  });

  /* Reveal ------------------------------------------------- */
  const revealItems = [...doc.querySelectorAll("[data-reveal]")];

  if ("IntersectionObserver" in window && !prefersReduced) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );

    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  /* Work preview + dialogs -------------------------------- */
  const workRows = [...doc.querySelectorAll("[data-case]")];
  const previews = [...doc.querySelectorAll("[data-preview]")];

  const activateCase = (slug) => {
    workRows.forEach((row) => row.classList.toggle("is-active", row.dataset.case === slug));
    previews.forEach((preview) => preview.classList.toggle("is-active", preview.dataset.preview === slug));
  };

  const unlockBody = () => {
    if (!doc.querySelector("dialog[open]") && menuToggle?.getAttribute("aria-expanded") !== "true") {
      doc.body.classList.remove("is-locked");
    }
  };

  const openCase = (slug, { push = true } = {}) => {
    const dialog = doc.getElementById(`case-${slug}`);
    if (!dialog) return;
    activateCase(slug);
    if (!dialog.open) dialog.showModal();
    doc.body.classList.add("is-locked");
    if (push && window.location.hash !== `#case-${slug}`) {
      try {
        history.pushState({ case: slug }, "", `#case-${slug}`);
      } catch (_) {
        /* history can be unavailable in embedded contexts */
      }
    }
  };

  const closeCase = (dialog, { updateHistory = true } = {}) => {
    if (!dialog || !dialog.open) return;
    dialog.close();
    unlockBody();
    if (!updateHistory) return;
    if (history.state && history.state.case) {
      history.back();
    } else if (window.location.hash.startsWith("#case-")) {
      try {
        history.replaceState(null, "", window.location.pathname + window.location.search);
      } catch (_) {
        /* history can be unavailable in embedded contexts */
      }
    }
  };

  const closeAllCases = () => {
    doc.querySelectorAll("dialog[open]").forEach((dialog) => {
      dialog.close();
    });
    unlockBody();
  };

  const syncCaseFromHash = () => {
    closeAllCases();
    if (window.location.hash.startsWith("#case-")) {
      openCase(window.location.hash.slice("#case-".length), { push: false });
    }
  };

  workRows.forEach((row) => {
    row.addEventListener("mouseenter", () => activateCase(row.dataset.case));
    row.addEventListener("focus", () => activateCase(row.dataset.case));

    row.addEventListener("click", () => openCase(row.dataset.case));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openCase(row.dataset.case);
      }
    });
  });

  doc.querySelectorAll(".case-dialog").forEach((dialog) => {
    dialog.querySelector("[data-close-dialog]")?.addEventListener("click", () => closeCase(dialog));

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeCase(dialog);
    });

    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeCase(dialog);
    });

    dialog.addEventListener("close", unlockBody);
  });

  doc.querySelectorAll("[data-case-cta]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const dialog = link.closest("dialog");
      if (dialog) {
        dialog.close();
        unlockBody();
      }

      try {
        history.replaceState(null, "", "#contact");
      } catch (_) {
        /* history can be unavailable in embedded contexts */
      }

      doc.getElementById("contact")?.scrollIntoView({
        behavior: prefersReduced ? "auto" : "smooth",
        block: "start",
      });
    });
  });

  window.addEventListener("popstate", syncCaseFromHash);

  const initialCase = window.location.hash.startsWith("#case-")
    ? window.location.hash.slice("#case-".length)
    : "";
  if (initialCase) openCase(initialCase, { push: false });

  doc.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (menuToggle?.getAttribute("aria-expanded") === "true") setMenu(false);
      const openDialog = doc.querySelector("dialog[open]");
      if (openDialog) closeCase(openDialog);
      return;
    }

    if (
      event.key === "Tab" &&
      menuToggle?.getAttribute("aria-expanded") === "true" &&
      menuFocusables.length
    ) {
      const first = menuFocusables[0];
      const last = menuFocusables[menuFocusables.length - 1];
      if (event.shiftKey && doc.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && doc.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  /* FAQ: close other items --------------------------------- */
  const faqItems = [...doc.querySelectorAll(".faq-item")];
  faqItems.forEach((item) => {
    item.addEventListener("toggle", () => {
      if (!item.open) return;
      faqItems.forEach((other) => {
        if (other !== item) other.open = false;
      });
    });
  });

  /* Mobile sticky CTA ------------------------------------- */
  const mobileCta = doc.getElementById("mobile-cta");
  const contactSection = doc.getElementById("contact");
  if (mobileCta && contactSection) {
    let contactInView = false;
    const updateCta = () => {
      const pastHero = window.scrollY > window.innerHeight * 0.65;
      mobileCta.classList.toggle("is-visible", pastHero && !contactInView);
    };

    if ("IntersectionObserver" in window) {
      const contactObserver = new IntersectionObserver(
        (entries) => {
          contactInView = entries[0]?.isIntersecting || false;
          updateCta();
        },
        { threshold: 0.15 }
      );
      contactObserver.observe(contactSection);
    }

    updateCta();
    window.addEventListener("scroll", updateCta, { passive: true });
    window.addEventListener("resize", updateCta);
  }

  /* Keep the language switch on the current section ------- */
  if (window.location.hash) {
    doc.querySelectorAll(".lang-switch").forEach((link) => {
      link.href = link.href.split("#")[0] + window.location.hash;
    });
  }

  root.classList.add("js-ready");
})();
