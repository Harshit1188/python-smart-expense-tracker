
document.addEventListener("DOMContentLoaded", function () {

    // ==================================
    // 1. DARK MODE
    // ==================================

    const themeButton = document.getElementById("themeToggle");

    function applyTheme(isDark) {
        document.body.classList.toggle("dark", isDark);

        if (themeButton) {
            themeButton.textContent = isDark ? "☀️ Light Mode" : "🌙 Dark Mode";
        }

        try {
            localStorage.setItem("expenseTheme", isDark ? "dark" : "light");
        } catch (error) {
            console.warn("Theme preference could not be saved.");
        }
    }

    let savedTheme = "light";

    try {
        savedTheme = localStorage.getItem("expenseTheme") || "light";
    } catch (error) {
        console.warn("Could not read saved theme.");
    }

    applyTheme(savedTheme === "dark");

    if (themeButton) {
        themeButton.addEventListener("click", function () {
            const isDark = !document.body.classList.contains("dark");
            applyTheme(isDark);
            updateChartTheme();
        });
    }


    // ==================================
    // 2. CHART DATA
    // ==================================

    function readChartData(id) {
        const canvas = document.getElementById(id);

        if (!canvas) {
            return { labels: [], values: [] };
        }

        try {
            return {
                labels: JSON.parse(canvas.dataset.labels || "[]"),
                values: JSON.parse(canvas.dataset.values || "[]")
            };
        } catch (error) {
            console.error("Chart data error:", id, error);
            return { labels: [], values: [] };
        }
    }


    // ==================================
    // 3. CHART COLORS
    // ==================================

    const chartColors = [
        "#5969ed",
        "#16a085",
        "#f5a142",
        "#9b59b6",
        "#e45b6b",
        "#22a6b3",
        "#64748b",
        "#d97706"
    ];

    let categoryChart = null;
    let monthlyChart = null;

    function isDarkMode() {
        return document.body.classList.contains("dark");
    }

    function chartTextColor() {
        return isDarkMode() ? "#edf1fb" : "#68738a";
    }

    function chartGridColor() {
        return isDarkMode() ? "#303b4f" : "#e8ebf2";
    }


    // ==================================
    // 4. CATEGORY DOUGHNUT CHART
    // ==================================

    function createCategoryChart() {

        const canvas = document.getElementById("categoryChart");

        if (!canvas || typeof Chart === "undefined") return;

        const data = readChartData("categoryChart");

        if (categoryChart) {
            categoryChart.destroy();
        }

        categoryChart = new Chart(canvas, {
            type: "doughnut",

            data: {
                labels: data.labels,

                datasets: [{
                    data: data.values,
                    backgroundColor: chartColors,
                    borderWidth: 2,
                    borderColor: isDarkMode() ? "#192131" : "#ffffff",
                    hoverOffset: 8
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: chartTextColor(),
                            padding: 15,
                            usePointStyle: false
                        }
                    }
                },

                cutout: "58%"
            }
        });
    }


    // ==================================
    // 5. MONTHLY SPENDING TREND
    // ==================================

    function createMonthlyChart() {

        const canvas = document.getElementById("monthlyChart");

        if (!canvas || typeof Chart === "undefined") return;

        const data = readChartData("monthlyChart");

        if (monthlyChart) {
            monthlyChart.destroy();
        }

        const parent = canvas.parentElement;
        let emptyMessage = parent.querySelector(".chart-empty");

        if (emptyMessage) {
            emptyMessage.remove();
        }

        if (!data.labels.length || !data.values.length) {

            canvas.style.display = "none";

            emptyMessage = document.createElement("div");
            emptyMessage.className = "chart-empty";
            emptyMessage.textContent =
                "No monthly expense data available yet. Add expenses to see your spending trend.";

            emptyMessage.style.cssText = `
                position: absolute;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                padding: 25px;
                color: ${chartTextColor()};
                font-size: 14px;
            `;

            parent.appendChild(emptyMessage);
            return;
        }

        canvas.style.display = "block";

        monthlyChart = new Chart(canvas, {

            type: "bar",

            data: {
                labels: data.labels,

                datasets: [{
                    label: "Monthly Expenses (₹)",
                    data: data.values,

                    backgroundColor: "#5969ed",
                    borderRadius: 8,
                    maxBarThickness: 55
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        labels: {
                            color: chartTextColor()
                        }
                    }
                },

                scales: {

                    x: {
                        ticks: {
                            color: chartTextColor()
                        },

                        grid: {
                            display: false
                        }
                    },

                    y: {
                        beginAtZero: true,

                        ticks: {
                            color: chartTextColor()
                        },

                        grid: {
                            color: chartGridColor()
                        }
                    }
                }
            }
        });
    }


    // ==================================
    // 6. UPDATE CHARTS AFTER THEME CHANGE
    // ==================================

    function updateChartTheme() {
        createCategoryChart();
        createMonthlyChart();
    }

    createCategoryChart();
    createMonthlyChart();


    // ==================================
    // 7. BUDGET PROGRESS BAR
    // ==================================

    const progress = document.getElementById("budgetProgress");

    if (progress) {

        const spent = Number(progress.dataset.spent || 0);
        const budget = Number(progress.dataset.budget || 0);

        let percentage = 0;

        if (budget > 0) {
            percentage = Math.min((spent / budget) * 100, 100);
        }

        progress.style.width = percentage + "%";

        if (spent > budget && budget > 0) {
            progress.classList.add("over");
        }
    }


    // ==================================
    // 8. EXPENSE SEARCH
    // ==================================

    const searchInput = document.getElementById("expenseSearch");
    const expenseTable = document.getElementById("expenseTable");

    if (searchInput && expenseTable) {

        searchInput.addEventListener("input", function () {

            const searchValue = searchInput.value.toLowerCase();

            const rows = expenseTable.querySelectorAll("tbody tr");

            rows.forEach(function (row) {

                const rowText = row.textContent.toLowerCase();

                row.style.display =
                    rowText.includes(searchValue) ? "" : "none";

            });
        });
    }


    // ==================================
    // 9. DELETE CONFIRMATION
    // ==================================

    document.querySelectorAll(".delete-btn").forEach(function (button) {

        button.addEventListener("click", function (event) {

            const confirmed = confirm(
                "Are you sure you want to delete this expense?"
            );

            if (!confirmed) {
                event.preventDefault();
            }

        });
    });


    // ==================================
    // 10. ADD EXPENSE FORM VALIDATION
    // ==================================

    const expenseForm = document.getElementById("expenseForm");

    if (expenseForm) {

        expenseForm.addEventListener("submit", function (event) {

            const title = expenseForm.querySelector(
                '[name="title"]'
            );

            const amount = expenseForm.querySelector(
                '[name="amount"]'
            );

            const category = expenseForm.querySelector(
                '[name="category"]'
            );

            const date = expenseForm.querySelector(
                '[name="expense_date"]'
            );

            if (
                !title.value.trim() ||
                !category.value ||
                !date.value ||
                Number(amount.value) <= 0
            ) {

                event.preventDefault();

                alert("Please enter valid details in all fields.");
            }
        });
    }

});
