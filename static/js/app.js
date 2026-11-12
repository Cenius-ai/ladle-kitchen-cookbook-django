/* Ladle Kitchen Cookbook — the one static script.
   Progressive enhancement only: every control in the templates is a real
   link, button or form and works before this file runs. */
(function () {
  "use strict";

  function all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function one(selector, root) {
    return (root || document).querySelector(selector);
  }

  /* ---------------------------------------------------------------- forms */
  function initBusyForms() {
    all("form[data-busy-form]").forEach(function (form) {
      var locked = false;
      var submitter = form.querySelector("button[type='submit'], input[type='submit']");
      if (!submitter) {
        return;
      }
      if (!submitter.hasAttribute("data-idle-label")) {
        submitter.setAttribute("data-idle-label", submitter.textContent.trim());
      }

      form.addEventListener("submit", function (event) {
        if (locked) {
          event.preventDefault();
          return;
        }
        locked = true;
        // Defer so the browser serialises the form before the button disables.
        window.setTimeout(function () {
          submitter.dataset.busy = "true";
          submitter.disabled = true;
          var label = submitter.getAttribute("data-busy-label");
          if (label) {
            submitter.textContent = label;
          }
        }, 0);

        // Never leave a form locked if the navigation was blocked.
        window.setTimeout(function () {
          if (document.body.contains(form)) {
            locked = false;
            submitter.disabled = false;
            delete submitter.dataset.busy;
            var original = submitter.getAttribute("data-idle-label");
            if (original) {
              submitter.textContent = original;
            }
          }
        }, 12000);
      });
    });
  }

  /* ------------------------------------------------------- password toggle */
  function initPasswordToggles() {
    all("[data-toggle-password]").forEach(function (button) {
      var input = document.getElementById(button.getAttribute("data-toggle-password"));
      if (!input) {
        return;
      }
      button.addEventListener("click", function () {
        var showing = input.type === "text";
        input.type = showing ? "password" : "text";
        button.textContent = showing ? "Show" : "Hide";
        button.setAttribute("aria-pressed", showing ? "false" : "true");
        input.focus();
      });
    });
  }

  /* --------------------------------------------------------- copy to board */
  function initCopyButtons() {
    all("[data-copy-target]").forEach(function (button) {
      var input = document.getElementById(button.getAttribute("data-copy-target"));
      if (!input) {
        return;
      }
      var status = one("[data-copy-status]", button.closest(".panel") || document);
      button.addEventListener("click", function () {
        var text = input.value;
        function done(message) {
          if (status) {
            status.textContent = message;
          }
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            done("Join link copied.");
          }, function () {
            input.select();
            done("Press Ctrl/Cmd + C to copy the selected link.");
          });
        } else {
          input.select();
          done("Press Ctrl/Cmd + C to copy the selected link.");
        }
      });
    });
  }

  /* --------------------------------------------------- image cover fallback */
  function initImageFallbacks() {
    all("img[data-img-fallback]").forEach(function (image) {
      var fallback = image.getAttribute("data-img-fallback");
      if (!fallback) {
        return;
      }
      function swap() {
        if (image.src.indexOf(fallback) === -1) {
          image.src = fallback;
        }
      }
      image.addEventListener("error", swap);
      if (image.complete && image.naturalWidth === 0) {
        swap();
      }
    });
  }

  /* ------------------------------------------------------- command palette */
  function initPalette() {
    var overlay = one("[data-cmdk]");
    if (!overlay) {
      return;
    }

    var items = [];
    try {
      items = JSON.parse(document.body.getAttribute("data-palette") || "[]") || [];
    } catch (error) {
      items = [];
    }
    if (!items.length) {
      return;
    }

    var input = one("[data-cmdk-input]", overlay);
    var list = one("[data-cmdk-results]", overlay);
    var openers = all("[data-cmdk-open]");
    var visible = [];
    var activeIndex = 0;

    function fuzzy(item, query) {
      if (!query) {
        return true;
      }
      var haystack = (item.label + " " + item.hint).toLowerCase();
      var cursor = 0;
      for (var i = 0; i < query.length; i += 1) {
        cursor = haystack.indexOf(query.charAt(i), cursor);
        if (cursor === -1) {
          return false;
        }
        cursor += 1;
      }
      return true;
    }

    function paintSelection() {
      all(".cmdk-item", list).forEach(function (node, index) {
        var selected = index === activeIndex;
        node.setAttribute("aria-selected", selected ? "true" : "false");
        if (selected && node.scrollIntoView) {
          node.scrollIntoView({ block: "nearest" });
        }
      });
    }

    function render(query) {
      visible = items.filter(function (item) {
        return fuzzy(item, query);
      }).slice(0, 12);
      list.textContent = "";

      if (!visible.length) {
        var empty = document.createElement("li");
        empty.className = "cmdk-empty";
        empty.textContent = "Nothing matches that search.";
        list.appendChild(empty);
        return;
      }
      if (activeIndex > visible.length - 1) {
        activeIndex = 0;
      }
      visible.forEach(function (item, index) {
        var row = document.createElement("li");
        var link = document.createElement("a");
        link.className = "cmdk-item";
        link.href = item.url;
        link.setAttribute("role", "option");
        link.setAttribute("aria-selected", index === activeIndex ? "true" : "false");

        var label = document.createElement("span");
        label.textContent = item.label;
        var hint = document.createElement("span");
        hint.className = "cmdk-item-hint";
        hint.textContent = item.hint;

        link.appendChild(label);
        link.appendChild(hint);
        link.addEventListener("mouseenter", function () {
          activeIndex = index;
          paintSelection();
        });
        row.appendChild(link);
        list.appendChild(row);
      });
    }

    function open() {
      overlay.hidden = false;
      input.value = "";
      activeIndex = 0;
      render("");
      input.focus();
    }

    function close() {
      overlay.hidden = true;
    }

    input.addEventListener("input", function () {
      activeIndex = 0;
      render(input.value.trim().toLowerCase());
    });

    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) {
        close();
      }
    });

    openers.forEach(function (opener) {
      opener.addEventListener("click", open);
    });

    document.addEventListener("keydown", function (event) {
      var isOpen = !overlay.hidden;
      if ((event.key === "k" || event.key === "K") && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        if (isOpen) {
          close();
        } else {
          open();
        }
        return;
      }
      if (!isOpen) {
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        activeIndex = Math.min(activeIndex + 1, Math.max(visible.length - 1, 0));
        paintSelection();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        paintSelection();
      } else if (event.key === "Enter") {
        var target = visible[activeIndex];
        if (target) {
          event.preventDefault();
          window.location.assign(target.url);
        }
      }
    });
  }

  /* ------------------------------------------------------------------------
     Cook-along mode: hands-free step paging.
     One step is visible at a time; the visible index moves by tapping
     Back / Repeat / Next, by the left/right arrow keys, or by voice
     ("next", "back", "repeat") through the browser SpeechRecognition API.
     Every path is a plain progressive enhancement — with JavaScript off the
     whole method is still on the page as an ordered list.
     ---------------------------------------------------------------------- */
  function initCookAlong() {
    var root = one("[data-cook-along]");
    if (!root) {
      return;
    }

    var steps = all("[data-cook-step]", root);
    if (!steps.length) {
      steps = all("[data-step]", root);
    }
    if (!steps.length) {
      return;
    }

    var total = steps.length;
    var index = 0;
    var counter = one("[data-cook-counter]", root);
    var progress = one("[data-cook-progress]", root);
    var progressbar = one("[data-cook-progressbar]", root);
    var status = one("[data-voice-status]", root);
    var voiceButton = one("[data-voice-toggle]", root);

    function setStatus(text, state) {
      if (!status) {
        return;
      }
      status.textContent = text;
      if (state) {
        status.setAttribute("data-state", state);
      } else {
        status.removeAttribute("data-state");
      }
    }

    function show(next) {
      index = Math.min(Math.max(next, 0), total - 1);
      steps.forEach(function (step, position) {
        if (position === index) {
          step.setAttribute("data-active", "true");
        } else {
          step.removeAttribute("data-active");
        }
      });
      if (counter) {
        counter.textContent = "Step " + (index + 1) + " of " + total;
      }
      if (progress) {
        progress.style.transform = "scaleX(" + (index + 1) / total + ")";
      }
      if (progressbar) {
        progressbar.setAttribute("aria-valuenow", String(index + 1));
      }
      // Observable state for tests and for anyone reading the DOM.
      root.setAttribute("data-cook-index", String(index));
    }

    function stepText() {
      return (steps[index].textContent || "").trim();
    }

    all("[data-cook-action]", root).forEach(function (button) {
      button.addEventListener("click", function () {
        var action = button.getAttribute("data-cook-action");
        if (action === "next") {
          show(index + 1);
        } else if (action === "back") {
          show(index - 1);
        } else if (action === "repeat") {
          setStatus("Repeating step " + (index + 1) + ": " + stepText(), "listening");
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      var tag = (event.target && event.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        show(index + 1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        show(index - 1);
      }
    });

    var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    var recognition = null;
    var listening = false;
    var manualStop = false;
    var watchdog = null;

    function syncButton() {
      if (!voiceButton) {
        return;
      }
      if (listening) {
        voiceButton.setAttribute("aria-pressed", "true");
        voiceButton.textContent = "Voice: on";
      } else {
        voiceButton.setAttribute("aria-pressed", "false");
        voiceButton.textContent = "Voice: off";
      }
    }

    function handlePhrase(transcript) {
      if (!transcript) {
        return;
      }
      if (/\b(next|forward|continue|onward)\b/.test(transcript)) {
        show(index + 1);
        setStatus("Heard: next — step " + (index + 1) + " of " + total + ".", "listening");
      } else if (/\b(back|previous|last)\b/.test(transcript)) {
        show(index - 1);
        setStatus("Heard: back — step " + (index + 1) + " of " + total + ".", "listening");
      } else if (/\b(repeat|again|say again)\b/.test(transcript)) {
        setStatus("Heard: repeat — " + stepText(), "listening");
      } else {
        setStatus("Heard: “" + transcript + "”. Say next, back or repeat.", "listening");
      }
    }

    function startListening() {
      if (!Recognition) {
        setStatus(
          "Voice is not available in this browser (or this page is not on HTTPS). The buttons and arrow keys still work.",
          "error"
        );
        syncButton();
        return;
      }
      if (!recognition) {
        recognition = new Recognition();
        recognition.lang = "en-GB";
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.maxAlternatives = 3;

        recognition.onstart = function () {
          window.clearTimeout(watchdog);
          watchdog = null;
          listening = true;
          manualStop = false;
          syncButton();
          setStatus("Listening — say next, back or repeat.", "listening");
        };

        recognition.onresult = function (event) {
          for (var i = event.resultIndex; i < event.results.length; i += 1) {
            var transcript = (event.results[i][0].transcript || "").toLowerCase().trim();
            handlePhrase(transcript);
          }
        };

        recognition.onerror = function (event) {
          if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            manualStop = true;
            listening = false;
            setStatus("Microphone permission was denied — use the buttons or the arrow keys.", "error");
          } else if (event.error === "no-speech" || event.error === "aborted") {
            return;
          } else {
            setStatus("Voice stopped (" + event.error + "). The buttons still work.", "error");
          }
          syncButton();
        };

        recognition.onend = function () {
          listening = false;
          syncButton();
          if (!manualStop) {
            window.setTimeout(function () {
              if (!manualStop) {
                try {
                  recognition.start();
                } catch (error) {
                  setStatus("Voice paused. Toggle it on again, or use the buttons.", "error");
                }
              }
            }, 400);
          }
        };
      }

      manualStop = false;
      listening = true;
      syncButton();
      setStatus("Listening — say next, back or repeat.", "listening");

      try {
        recognition.start();
      } catch (error) {
        listening = false;
        syncButton();
        setStatus("Voice could not start — use the buttons or the arrow keys.", "error");
        return;
      }

      // Some browsers accept start() and then never answer (no engine, no
      // microphone, blocked permission). Say so instead of pretending.
      window.clearTimeout(watchdog);
      watchdog = window.setTimeout(function () {
        if (listening && !manualStop) {
          listening = false;
          manualStop = true;
          syncButton();
          setStatus(
            "Voice is not responding — check the microphone permission, or keep using the buttons and arrow keys.",
            "error"
          );
          try {
            recognition.stop();
          } catch (error) {
            /* already stopped */
          }
        }
      }, 2500);
    }

    function stopListening() {
      manualStop = true;
      listening = false;
      if (recognition) {
        try {
          recognition.stop();
        } catch (error) {
          /* already stopped */
        }
      }
      syncButton();
      setStatus("Voice off — taps and the arrow keys always work.", null);
    }

    if (voiceButton) {
      voiceButton.addEventListener("click", function () {
        if (listening) {
          stopListening();
        } else {
          startListening();
        }
      });
    }

    document.addEventListener("visibilitychange", function () {
      if (document.hidden && listening) {
        stopListening();
      }
    });

    show(0);
    if (!Recognition) {
      setStatus("Voice is not available in this browser — the buttons and arrow keys still work.", "error");
    }
  }

  function boot() {
    initBusyForms();
    initPasswordToggles();
    initCopyButtons();
    initImageFallbacks();
    initPalette();
    initCookAlong();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
