const SEND_THROTTLE_MS = 100

let doubleTapCounter = 0

let nextInputSendAllowed = 0
let connectionAttempts = 0
let nextConnectionAttempt = 0
let webSocket

let zones
let sources

let showingLoading = false

const container = $("#container")

showConnectingScreen("server")
setCustomValues()
connectWebSocket()

function connectWebSocket() {
    webSocket = new WebSocket(`ws://${HOST}:8765`);
    webSocket.onmessage = function (event) {
        console.log(event.data);
        jsn = JSON.parse(event.data)
        var responseType = jsn["responseType"]
        if (responseType === "state") {
            if (showingLoading) {
                setupPage()
            }
            setState(jsn["data"]);
        } else if (responseType === "noAmp") {
            showConnectingScreen("amplifier")
        }
    }

    webSocket.onopen = function () {
        connectionAttempts = 0
        getState(-1)
    }

    webSocket.onclose = function () {
        if (connectionAttempts === 0) {
            showConnectingScreen("server")
        }
        attemptReconnect()
    }
}

function attemptReconnect() {
    setTimeout(() => {
        const nextReconnectionTime = Math.round((nextConnectionAttempt - now()) / 1000)
        let txt = "Attempting to reconnect"
        if (nextReconnectionTime > 0) {
            txt = `Attempting to reconnect in ${nextReconnectionTime} seconds`
            $("#reconnect-button").removeClass("w3-disabled")
        } else {
            $("#reconnect-button").addClass("w3-disabled")
        }
        $("#reset_timer").html(txt)
        if (now() > nextConnectionAttempt) {
            connectionAttempts++
            connectWebSocket()
            nextConnectionAttempt = now() + (connectionAttempts <= 10 ? connectionAttempts * 2000 : 20000)
        } else {
            if (webSocket.readyState != WebSocket.OPEN) {
                attemptReconnect()
            }
        }
    }, 1000)
}

function showConnectingScreen(target) {
    showingLoading = true
    let newContent = `<div class="w3-card w3-container w3-center w3-theme-l4">`
    newContent += `<div class="same-row">`
    newContent += `<h3>Connecting to ${target}</h3>`
    newContent += `<img id="reconnect-spinner" class="w3-spin" src="assets/img/spinner-of-dots.png"/>`
    newContent += `</div>`
    newContent += `<p id="reset_timer">Attempting to connect to ${target}</p>`
    newContent += `<button id="reconnect-button" class="w3-margin-bottom w3-button w3-light-grey w3-disabled" onclick="forceReconnect()">Force reconnect</button>`
    container.html(newContent)
}

function forceReconnect() {
    nextConnectionAttempt = 0
}

function setupPage() {
    let newContent = `<table class="w3-table-all w3-card">`
    for (let i = 0; i < 7; i++) {
        newContent += `<tr class=""><td>`
        newContent += `<h3 id="zone_id_header" class="center" onclick="toggleAdvancedSettings(${i})">${zones[i]}</h3>`
        newContent += `<div class="w3-row-padding">`
        newContent += `<div class="w3-half same-row">`
        newContent += createPowerButton(i, "w3-margin-right")
        newContent += createSourceSelector(i, container, "")
        newContent += `</div>`
        newContent += createSlider(i, "volume", "w3-half w3-margin-top")
        newContent += `</div>`

        //Ugly hack to keep rows alternating correctly
        newContent += `<tr style="display: none;"><td>`
        newContent += `</td></tr>`

        newContent += `<tr id="channel_${i}_advanced" class="w3-hide w3-dark-grey"><td class="advanced-row">`
        newContent += `<table>`
        newContent += createNamedSliderTableRow(i, "bass")
        newContent += createNamedSliderTableRow(i, "treble")
        newContent += createNamedSliderTableRow(i, "balance")
        newContent += `</table>`
        newContent += `</td></tr>`
        newContent += `</td></tr>`
    }
    newContent += `</table>`
    container.html(newContent)
    showingLoading = false
}

function createNamedSliderTableRow(id, name) {
    return `<tr class="w3-dark-grey" onclick="resetSlider(${id}, '${name}')"><td>${name}</td><td>${createSlider(id, name, "")}</td></tr>`
}

function resetSlider(id, name) {
    doubleTapCounter++
    if (doubleTapCounter > 3) {
        doubleTapCounter = 0
        $(`#zone_${id}_${name}`).val(50)
        jsn = {}
        jsn["value"] = 50
        jsn["type"] = name
        sendCommand(id, jsn)
    } else {
        setTimeout(() => { Math.max(doubleTapCounter - 1, 0); }, 1000)
    }
}

function toggleAdvancedSettings(id) {
    const advancedSettings = $(`#channel_${id}_advanced`)
    advancedSettings.toggleClass("w3-hide")
    advancedSettings.toggleClass("w3-show")
}

function createPowerButton(id, classes) {
    return powerIcon(`zone_${id}_power`, `svg-icon-small svg-light-grey ${classes}`, `handlePowerButton(${id})`)
}

function createSlider(id, type, classes) {
    const html_id = `zone_${id}_${type}`
    return `<input type="range" min="0" id="${html_id}" class="slider ${classes}" max="100" oninput="handleSlider(${id}, '${type}')">`
}

function createSourceSelector(zoneId, html, classes) {
    const html_id = `zone_${zoneId}_source`
    let sourceSelector = `<select id="${html_id}" class="w3-select ${classes}" onchange="handleInputChanged(${zoneId}, this.selectedIndex)">`;
    let i = 0
    sources.forEach(source => {
        sourceSelector += `<option value="${i}">${source}</option>`
        i++;
    })
    sourceSelector += "</select>"
    return sourceSelector
}

function handleInputChanged(id, inputId) {
    console.log(`Input changed to ${sources[inputId]} for ${zones[id]}`)
    jsn = {}
    jsn["value"] = inputId
    jsn["type"] = "input"
    sendCommand(id, jsn)
}

function handlePowerButton(id) {
    jsn = {}
    jsn["type"] = "power"
    jsn["value"] = "toggle"
    sendCommand(id, jsn)
    setPowerButtonState(id, $(`#zone_${id}_power`).hasClass("power-button-off"))
}

function getState(zoneId) {
    jsn = {
        "operation": "getState"
        , "id": zoneId
    }
    webSocket.send(JSON.stringify(jsn))
}

function handleSlider(id, type) {
    const t = now()
    if (t > nextInputSendAllowed) {
        setTimeout(() => {
            jsn = {}
            jsn["value"] = $(`#zone_${id}_${type}`).val()
            jsn["type"] = type
            sendCommand(id, jsn)
        }, SEND_THROTTLE_MS)
        nextInputSendAllowed = t + SEND_THROTTLE_MS;
    }
}

function setState(stateAsJson) {
    stateAsJson.forEach(function (state) {
        const channel = state["id"]
        setStatesFromJson(channel, state)
        setPowerButtonState(channel, state["powerOn"])
    })
}

function setPowerButtonState(id, powerOn) {
    const powerButton = $(`#zone_${id}_power`)
    if (powerOn) {
        powerButton.removeClass("power-button-off")
        powerButton.addClass("power-button-on")
    } else {
        powerButton.removeClass("power-button-on")
        powerButton.addClass("power-button-off")
    }
}

function setStatesFromJson(channel, key) {
    setObjectState(channel, "volume", key)
    setObjectState(channel, "source", key)
    setObjectState(channel, "treble", key)
    setObjectState(channel, "bass", key)
    setObjectState(channel, "balance", key)
}

function setObjectState(channel, key, json) {
    const object = $(`#zone_${channel}_${key}`)
    if (object) {
        object.val(json[key])
    }
}

function sendCommand(id, jsn) {
    jsn["operation"] = "command"
    jsn["id"] = id
    webSocket.send(JSON.stringify(jsn))

}

function now() {
    return (new Date).getTime();
}

function setCustomValues() {
    syncRequest("assets/config.json", result => {
        setCustomValuesFromJson(result)
    }, () => {
        syncRequest("assets/config.json", result => {
            setCustomValuesFromJson(result)
        })
    })
}

function syncRequest(path, onSuccess, onFail) {
    $.ajax({
        url: path,
        success: onSuccess,
        error: onFail,
        async: false
    })
}


function setCustomValuesFromJson(jsn) {
    zones = jsn["zones"]
    sources = jsn["sources"]
}
