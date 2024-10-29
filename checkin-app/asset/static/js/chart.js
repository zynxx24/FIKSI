// Fungsi untuk memperbarui chart dengan data dari backend
function updateChart(startDate, endDate) {
    fetch('/chart-data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            start_date: startDate,
            end_date: endDate
        }),
    })
    .then(response => response.json())
    .then(data => {
        // Update Chart.js dengan data yang baru
        checkinChart.data.labels = data.labels;
        checkinChart.data.datasets[0].data = data.checkin_counts;

        // Update chart untuk menampilkan perubahan
        checkinChart.update();

        // Update startDate dan endDate dengan tanggal yang ada di database jika tidak diberikan
        if (!startDate && !endDate) {
            startDate = data.start_date;
            endDate = data.end_date;
        }
    });
}

// Inisialisasi Chart.js
const ctx = document.getElementById('checkinChartContainer').getContext('2d');
const checkinChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], // Akan di-update saat data di-fetch
        datasets: [{
            label: 'Jumlah Check-in',
            data: [], // Akan di-update dengan data yang di-fetch
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderWidth: 1,
            fill: true,
            tension: 0.1, // Untuk menambah smooth pada garis chart
        }]
    },
    options: {
        responsive: true,
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Tanggal'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Jumlah Check-in'
                },
                beginAtZero: true
            }
        },
        plugins: {
            legend: {
                display: true,
                position: 'top',
            }
        }
    }
});

// Inisialisasi chart dengan rentang tanggal dari database
updateChart(null, null);

// Fungsi polling untuk update data setiap 30 detik
setInterval(() => {
    updateChart(null, null);
}, 30000);
