(function () {
  var panel = document.querySelector("[data-booking]");
  if (!panel) return;

  var calGrid = panel.querySelector("#calGrid");
  var slotGrid = panel.querySelector("#slotGrid");
  var title = panel.querySelector(".cal-title");
  var prev = panel.querySelector(".cal-nav[aria-label='上个月']");
  var next = panel.querySelector(".cal-nav[aria-label='下个月']");
  var submit = panel.querySelector("#bookSubmit");
  var status = panel.querySelector("#bookStatus");
  var locNote = panel.querySelector("#locNote");
  var now = new Date();
  var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var year = today.getFullYear();
  var month = today.getMonth();
  var selected = null;
  var dowLabels = ["日", "一", "二", "三", "四", "五", "六"];
  var slots = ["09:00", "10:30", "13:00", "14:30", "16:00", "19:30"];

  function sameMonth(y, m) {
    return y === today.getFullYear() && m === today.getMonth();
  }
  function iso(d) {
    var m = String(d.getMonth() + 1);
    var day = String(d.getDate());
    if (m.length < 2) m = "0" + m;
    if (day.length < 2) day = "0" + day;
    return d.getFullYear() + "-" + m + "-" + day;
  }
  function buildCal() {
    title.textContent = year + " 年 " + (month + 1) + " 月";
    prev.disabled = sameMonth(year, month);
    calGrid.innerHTML = "";
    dowLabels.forEach(function (label) {
      var dw = document.createElement("div");
      dw.className = "cal-dow";
      dw.textContent = label;
      calGrid.appendChild(dw);
    });
    var pad = new Date(year, month, 1).getDay();
    var total = new Date(year, month + 1, 0).getDate();
    var i;
    for (i = 0; i < pad; i++) {
      var blank = document.createElement("button");
      blank.type = "button";
      blank.className = "cal-date is-off";
      blank.tabIndex = -1;
      blank.disabled = true;
      calGrid.appendChild(blank);
    }
    for (var d = 1; d <= total; d++) {
      var date = new Date(year, month, d);
      var button = document.createElement("button");
      button.type = "button";
      button.className = "cal-date";
      button.textContent = String(d);
      button.setAttribute("aria-label", "选择 " + d + " 日");
      if (date < today) {
        button.classList.add("is-off");
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
      } else {
        if (selected && selected.getTime() === date.getTime()) {
          button.classList.add("is-selected");
          button.setAttribute("aria-pressed", "true");
        }
        button.addEventListener("click", function () {
          selected = new Date(year, month, Number(this.textContent));
          panel.dataset.date = iso(selected);
          calGrid.querySelectorAll(".cal-date").forEach(function (item) {
            item.classList.remove("is-selected");
            item.setAttribute("aria-pressed", "false");
          });
          this.classList.add("is-selected");
          this.setAttribute("aria-pressed", "true");
        });
      }
      calGrid.appendChild(button);
    }
  }
  function buildSlots() {
    slotGrid.innerHTML = "";
    slots.forEach(function (slot) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "slot";
      button.textContent = slot;
      button.addEventListener("click", function () {
        panel.dataset.time = slot;
        slotGrid.querySelectorAll(".slot").forEach(function (item) {
          item.classList.remove("is-selected");
          item.setAttribute("aria-pressed", "false");
        });
        this.classList.add("is-selected");
        this.setAttribute("aria-pressed", "true");
      });
      slotGrid.appendChild(button);
    });
  }

  prev.addEventListener("click", function () {
    if (sameMonth(year, month)) return;
    month -= 1;
    if (month < 0) { month = 11; year -= 1; }
    buildCal();
  });
  next.addEventListener("click", function () {
    month += 1;
    if (month > 11) { month = 0; year += 1; }
    buildCal();
  });
  buildCal();
  buildSlots();

  panel.querySelectorAll("input[name=bmode]").forEach(function (radio) {
    radio.addEventListener("change", function () {
      if (locNote) locNote.hidden = this.value !== "offline";
    });
  });

  function say(text, isError) {
    status.classList.toggle("is-error", !!isError);
    status.textContent = text;
  }

  submit.addEventListener("click", function () {
    var mode = panel.querySelector("input[name=bmode]:checked");
    var name = panel.querySelector("input[name=bname]").value.trim();
    var email = panel.querySelector("input[name=bemail]").value.trim();
    var contact = panel.querySelector("input[name=bcontact]").value.trim();
    var note = panel.querySelector("textarea[name=bnote]").value.trim();
    if (!panel.dataset.date || !panel.dataset.time) {
      say("请先选择日期和时间。", true);
      return;
    }
    if (!name || !email) {
      say("请留下姓名和邮箱。", true);
      return;
    }
    submit.disabled = true;
    say("正在提交预约请求。", false);
    fetch("/api/booking", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service: panel.getAttribute("data-booking"),
        mode: mode ? mode.value : "",
        date: panel.dataset.date,
        time: panel.dataset.time,
        name: name,
        email: email,
        contact: contact,
        note: note
      })
    }).then(function (res) {
      return res.json().then(function (data) { return { ok: res.ok, data: data }; });
    }).then(function (result) {
      var data = result.data || {};
      if (data.status === "REQUEST_RECEIVED") {
        say("预约请求已经提交。请求编号 " + data.request_id + "。这还不是一次已经确认的预约。容熙会用你留下的邮箱回复。这个时间还没有被占住，也还没有付款。", false);
        return;
      }
      if (data.status === "OPEN_MAIL" && typeof data.mailto === "string" && data.mailto.indexOf("mailto:") === 0) {
        status.classList.remove("is-error");
        status.textContent = "邮件窗口会打开一封写好的预约请求。需要由你发出那封邮件，容熙才能看到。这还不是一次已经确认的预约。";
        var link = document.createElement("a");
        link.href = data.mailto;
        link.textContent = "打开邮件，发出这次请求";
        status.appendChild(document.createElement("br"));
        status.appendChild(link);
        window.location.href = data.mailto;
        return;
      }
      if (data.status === "DELIVERY_NOT_CONFIGURED") {
        say("这次请求没有发出。预约收件还没有接上，所以现在还不能把请求送到容熙。", true);
        return;
      }
      if (data.status === "INVALID") {
        var fields = data.fields || [];
        if (fields.indexOf("date") >= 0 || fields.indexOf("time") >= 0) say("请先选择一个还没过去的日期和时间。", true);
        else if (fields.indexOf("email") >= 0) say("请留下一个可以回复的邮箱。", true);
        else say("请检查日期、时间和联系方式后再提交。", true);
        return;
      }
      say("这次请求没有发出。请稍后再试。", true);
    }).catch(function () {
      say("这次请求没有发出。请稍后再试。", true);
    }).then(function () {
      submit.disabled = false;
    });
  });
})();
