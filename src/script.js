let entries = JSON.parse(localStorage.getItem("fuelEntries")) || [];

/* ---------- UTIL ---------- */
function save() {
    localStorage.setItem("fuelEntries", JSON.stringify(entries));
}

function formatDate(d) {
    return new Date(d).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

/* ---------- CORE ---------- */
function addEntry() {
    const vehicle = document.getElementById("vehicle").value;
    const date = document.getElementById("date").value;
    const odo = parseFloat(document.getElementById("odometer").value);
    const fuel = parseFloat(document.getElementById("fuel").value);
    const cost = parseFloat(document.getElementById("cost").value);

    // Real validation (not superficial)
    if (!date || isNaN(odo) || isNaN(fuel) || isNaN(cost)) {
        alert("Invalid input");
        return;
    }

    if (fuel <= 0 || odo <= 0 || cost <= 0) {
        alert("Values must be positive");
        return;
    }

    entries.push({ vehicle, date, odo, fuel, cost });

    // Sort latest first
    entries.sort((a, b) => new Date(b.date) - new Date(a.date));

    save();
    render();
    clearForm();
}

function clearForm() {
    document.getElementById("date").value = "";
    document.getElementById("odometer").value = "";
    document.getElementById("fuel").value = "";
    document.getElementById("cost").value = "";
}

function calculateEconomy(index) {
    if (index === entries.length - 1) return null;

    const curr = entries[index];
    const next = entries[index + 1];

    const distance = curr.odo - next.odo;

    if (distance <= 0) return null;

    return (distance / curr.fuel).toFixed(1);
}

function deleteEntry(i) {
    if (!confirm("Delete entry?")) return;
    entries.splice(i, 1);
    save();
    render();
}

/* ---------- RENDER ---------- */
function render() {
    const tbody = document.getElementById("tableBody");
    tbody.innerHTML = "";

    entries.forEach((e, i) => {
        const eco = calculateEconomy(i);

        tbody.innerHTML += `
        <tr>
            <td>${formatDate(e.date)}</td>
            <td>${e.vehicle}</td>
            <td>${e.odo}</td>
            <td>${e.fuel}</td>
            <td>₹${e.cost}</td>
            <td>${eco ? `<span class="badge">${eco} km/L</span>` : "-"}</td>
            <td><span class="delete-btn" onclick="deleteEntry(${i})">🗑</span></td>
        </tr>`;
    });
}

/* ---------- INIT ---------- */
render();