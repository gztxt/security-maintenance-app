/* 安防维保管理系统 v2.1 — 纯 ES5 风格，兼容所有浏览器 */
(function(){

var curDate = "";
var curMonth = "";
var saveTimer = null;
var maxImgs = 4;

function getId(id) { return document.getElementById(id); }

/* ── 网络请求 ── */
function ajax(method, url, body, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader("Accept", "application/json");
    if (typeof body === "string") {
        xhr.setRequestHeader("Content-Type", "application/json");
    }
    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
            try { cb(null, JSON.parse(xhr.responseText)); }
            catch(e) { cb(e, null); }
        } else {
            cb(new Error("HTTP " + xhr.status), null);
        }
    };
    xhr.send(body || null);
}

function apiGet(url, cb) { ajax("GET", url, null, cb); }
function apiPost(url, body, cb) { ajax("POST", url, body, cb); }
function apiDelete(url, cb) { ajax("DELETE", url, null, cb); }
function apiUpload(url, fd, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
            try { cb(null, JSON.parse(xhr.responseText)); }
            catch(e) { cb(e, null); }
        } else {
            cb(new Error("HTTP " + xhr.status), null);
        }
    };
    xhr.send(fd);
}

/* ── Toast ── */
var toastTimer = null;
function showToast(msg, type) {
    var el = getId("toast");
    el.textContent = msg;
    el.className = "toast" + (type ? " " + type : "");
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function(){ el.classList.remove("show"); }, 2500);
}

/* ── 日志 ── */
function loadLog() {
    apiGet("/api/daily-log?date=" + curDate, function(err, d) {
        if (err) return;
        getId("iptLoc").value = d.data ? (d.data.locations || "") : "";
        getId("iptWork").value = d.data ? (d.data.work_log || "") : "";
    });
}

function saveLog() {
    // 工作内容自动合并换行为空格（PDF 版面有限，不保留手动换行）
    var workText = getId("iptWork").value;
    // 统一换行符为空格，连续多个空白压缩为一个
    workText = workText.replace(/\r\n|\n|\r/g, " ").replace(/\s+/g, " ").trim();
    var body = JSON.stringify({
        date: curDate,
        locations: getId("iptLoc").value,
        work_log: workText
    });
    apiPost("/api/daily-log", body, function(err, d) {
        var el = getId("saveStatus");
        if (err || !d.success) {
            el.textContent = "❌ 保存失败";
            el.className = "save-status error";
            return;
        }
        el.textContent = "✅ 已保存";
        el.className = "save-status saved";
        setTimeout(function(){ el.textContent = ""; el.className = "save-status"; }, 2000);
    });
}

function scheduleSave() {
    var el = getId("saveStatus");
    el.textContent = "⏳ 保存中...";
    el.className = "save-status saving";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveLog, 300);
}

/* ── 日期 ── */
function changeDate(delta) {
    var parts = curDate.split("-");
    var d = new Date(parseInt(parts[0],10), parseInt(parts[1],10)-1, parseInt(parts[2],10));
    d.setDate(d.getDate() + delta);
    var y = d.getFullYear();
    var m = ("0" + (d.getMonth()+1)).slice(-2);
    var day = ("0" + d.getDate()).slice(-2);
    curDate = y + "-" + m + "-" + day;
    getId("btnPickDate").textContent = curDate;
    loadLog();
    loadImages();
}

function openDatePicker() {
    // 手机兼容：iOS Safari / Android 均需 visible 且 focus 才能弹 picker
    var picker = document.createElement("input");
    picker.type = "date";
    picker.value = curDate;
    picker.style.cssText = "position:fixed;left:0;top:40%;width:100%;height:48px;font-size:18px;opacity:0.01;z-index:999999;";
    picker.setAttribute("autocomplete", "off");
    document.body.appendChild(picker);
    
    var handled = false;
    function done() {
        if (handled) return;
        handled = true;
        curDate = picker.value;
        getId("btnPickDate").textContent = curDate;
        loadLog();
        loadImages();
        // 延迟移除，避免切走时还在触发
        setTimeout(function() {
            if (document.body.contains(picker)) document.body.removeChild(picker);
        }, 100);
    }
    
    picker.addEventListener("input", done);
    picker.addEventListener("change", done);
    
    // 点击外部或取消时移除
    function onTouch(e) {
        if (e.target !== picker && !handled) {
            handled = true;
            if (document.body.contains(picker)) document.body.removeChild(picker);
            document.removeEventListener("touchstart", onTouch);
            document.removeEventListener("mousedown", onTouch);
        }
    }
    setTimeout(function() {
        document.addEventListener("touchstart", onTouch);
        document.addEventListener("mousedown", onTouch);
    }, 300);
    
    // 在手机上用 focus + click 同时触发，确保弹出来
    picker.focus();
    setTimeout(function() { picker.click(); }, 50);
    setTimeout(function() { picker.showPicker && picker.showPicker(); }, 100);
}

/* ── 图片 ── */
function loadImages() {
    var grid = getId("imgGrid");
    grid.innerHTML = "";
    apiGet("/api/images/" + curDate, function(err, d) {
        var imgs = d && d.data ? d.data : [];
        var i;
        for (i = 0; i < maxImgs; i++) {
            var slot = document.createElement("div");
            slot.className = "image-slot";
            if (i < imgs.length) {
                (function(idx) {
                    var img = imgs[idx];
                    slot.innerHTML = '<img src="' + img.thumbnail + '" alt="照片" class="uniform-img">';
                    var del = document.createElement("button");
                    del.className = "delete-btn";
                    del.textContent = "×";
                    del.onclick = function(e) {
                        e.stopPropagation();
                        deletePicture(img.index);
                    };
                    slot.appendChild(del);
                })(i);
            } else if (i === imgs.length && imgs.length < maxImgs) {
                slot.innerHTML = '<div class="placeholder">📷</div><div class="add-label">拍照/选取</div>';
                slot.onclick = openAlbum;
            } else {
                slot.style.cssText = "border:none;background:transparent;";
            }
            grid.appendChild(slot);
        }
    });
}

function openAlbum() {
    getId("albumInput").value = "";
    getId("albumInput").click();
}

function handleAlbumFiles() {
    handleFiles(getId("albumInput").files);
}

function handleFiles(files) {
    if (!files || !files.length) return;
    var fd = new FormData();
    var max = Math.min(files.length, maxImgs);
    for (var i = 0; i < max; i++) fd.append("images", files[i]);
    apiUpload("/api/upload-image/" + curDate, fd, function(err, d) {
        if (d && d.success) {
            showToast("已上传 " + d.data.length + " 张", "success");
            loadImages();
        } else {
            showToast("上传失败", "error");
        }
    });
}

function deletePicture(idx) {
    if (!confirm("删除这张照片？")) return;
    apiDelete("/api/delete-image/" + curDate + "/" + idx, function(err, d) {
        if (d && d.success) { showToast("已删除", "success"); loadImages(); }
    });
}

/* ── 报告 ── */
function loadReports() {
    apiGet("/api/reports", function(err, d) {
        var list = getId("reportList");
        var reports = d && d.data ? d.data : [];
        if (!reports.length) {
            list.innerHTML = '<div class="empty-state"><div class="empty-icon">📄</div><div>暂无报告</div></div>';
            return;
        }
        var html = "";
        for (var i = 0; i < reports.length; i++) {
            var r = reports[i];
            html += '<div class="report-item"><div><div class="report-name">' + r.name + '</div><div class="report-meta">' + r.modified + ' · ' + (r.size/1024).toFixed(0) + 'KB</div></div><div class="report-actions"><a class="btn btn-sm btn-primary" href="' + r.url + '" target="_blank">查看</a><a class="btn btn-sm btn-gold" href="' + r.url + '" download>下载</a></div></div>';
        }
        list.innerHTML = html;
    });
}

function initMonthPicker() {
    var now = new Date();
    var curY = now.getFullYear();
    var curM = now.getMonth() + 1;
    
    var yearSel = getId("inpYear");
    var monthSel = getId("inpMonth");
    
    // 填充年份：当前年-3 到 当前年+1
    for (var y = curY - 3; y <= curY + 1; y++) {
        var opt = document.createElement("option");
        opt.value = y;
        opt.textContent = y + "年";
        if (y === curY) opt.selected = true;
        yearSel.appendChild(opt);
    }
    
    // 填充月份 1-12
    for (var m = 1; m <= 12; m++) {
        var opt = document.createElement("option");
        opt.value = m < 10 ? "0" + m : "" + m;
        opt.textContent = m + "月";
        if (m === curM) opt.selected = true;
        monthSel.appendChild(opt);
    }
}

function getSelectedMonth() {
    return getId("inpYear").value + "-" + getId("inpMonth").value;
}

function generateReport() {
    var month = getSelectedMonth();
    if (!month) { showToast("请选择月份", "error"); return; }
    showToast("正在生成...", "success");
    apiPost("/api/generate-report/" + month, null, function(err, d) {
        if (d && d.success) { showToast("报告生成成功！", "success"); loadReports(); }
        else { showToast(d ? d.message : "生成失败", "error"); }
    });
}

/* ── Tab ── */
function switchTab(tab) {
    var pages = document.querySelectorAll(".page-content");
    for (var i = 0; i < pages.length; i++) pages[i].classList.remove("active");
    getId("page-" + tab).classList.add("active");
    var items = document.querySelectorAll(".nav-item");
    for (var i = 0; i < items.length; i++) items[i].classList.remove("active");
    var sel = document.querySelector('.nav-item[data-tab="' + tab + '"]');
    if (sel) sel.classList.add("active");
    if (tab === "report") loadReports();
}

/* ── 设置 ── */
function saveSettings() {
    localStorage.setItem("project", getId("setProject").value);
    localStorage.setItem("client", getId("setClient").value);
    localStorage.setItem("contractor", getId("setContractor").value);
    showToast("设置已保存", "success");
}

/* ── 初始化 ── */
function init() {
    apiGet("/api/today", function(err, d) {
        if (err || !d.success) {
            showToast("加载失败", "error");
            return;
        }
        curDate = d.data.today;
        curMonth = d.data.month;
        getId("btnPickDate").textContent = curDate;
        getId("loading").style.display = "none";
        loadLog();
        loadImages();
        loadReports();

        // 初始化月份下拉
        initMonthPicker();

        // 加载保存的设置
        if (localStorage.getItem("project")) getId("setProject").value = localStorage.getItem("project");
        if (localStorage.getItem("client")) getId("setClient").value = localStorage.getItem("client");
        if (localStorage.getItem("contractor")) getId("setContractor").value = localStorage.getItem("contractor");
    });
}

/* ── 绑定事件 ── */
document.addEventListener("DOMContentLoaded", function() {

    // 日期导航
    getId("btnPrev").addEventListener("click", function(){ changeDate(-1); });
    getId("btnNext").addEventListener("click", function(){ changeDate(1); });
    getId("btnPickDate").addEventListener("click", openDatePicker);

    // 自动保存
    getId("iptLoc").addEventListener("input", scheduleSave);
    getId("iptLoc").addEventListener("blur", function(){ clearTimeout(saveTimer); saveLog(); });
    getId("iptWork").addEventListener("input", scheduleSave);
    getId("iptWork").addEventListener("blur", function(){ clearTimeout(saveTimer); saveLog(); });

    // 相册
    getId("albumInput").addEventListener("change", handleAlbumFiles);
    getId("btnAlbum").addEventListener("click", openAlbum);

    // 报告
    getId("btnGenReport").addEventListener("click", generateReport);

    // Tab 导航
    var navs = document.querySelectorAll(".nav-item");
    for (var i = 0; i < navs.length; i++) {
        (function(el) {
            el.addEventListener("click", function() {
                switchTab(el.getAttribute("data-tab"));
            });
        })(navs[i]);
    }

    // 设置
    getId("setProject").addEventListener("change", saveSettings);
    getId("setClient").addEventListener("change", saveSettings);
    getId("setContractor").addEventListener("change", saveSettings);

    // 启动
    init();
});

})();
