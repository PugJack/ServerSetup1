// Check if the bot is online and update UI accordingly
document.addEventListener('DOMContentLoaded', function() {
    console.log('Document loaded, checking bot status...');
    
    // Show bot status indicator
    const statusIndicator = document.createElement('div');
    statusIndicator.className = 'bot-status';
    statusIndicator.innerHTML = `
        <div class="container d-flex align-items-center justify-content-between p-2 rounded">
            <div>
                <span class="status-indicator status-pending"></span>
                <span class="status-text">Checking bot status...</span>
            </div>
            <div>
                <a href="https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands" 
                   class="btn btn-sm btn-outline-primary">Add to Discord</a>
            </div>
        </div>
    `;
    
    // Insert at the top of the main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertBefore(statusIndicator, mainContent.firstChild);
    }
    
    // Get bot status with retry
    function checkBotStatus(retries = 3) {
        console.log(`Checking bot status, retries left: ${retries}`);
        fetch('/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Status response:', data);
                if (data.status === "online") {
                    updateStatusIndicator(true);
                    console.log("Bot is online");
                } else {
                    updateStatusIndicator(false);
                    console.log("Bot is offline");
                }
            })
            .catch(error => {
                console.error('Error fetching bot status:', error);
                if (retries > 0) {
                    // Wait 1 second before retry
                    setTimeout(() => checkBotStatus(retries - 1), 1000);
                } else {
                    updateStatusIndicator(false);
                }
            });
    }
    
    // Update the status indicator in the UI
    function updateStatusIndicator(isOnline) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (statusIndicator && statusText) {
            // Remove the pending class
            statusIndicator.classList.remove('status-pending');
            
            if (isOnline) {
                statusIndicator.classList.add('status-online');
                statusText.textContent = 'ServerSetup Bot is online';
            } else {
                statusIndicator.classList.add('status-offline');
                statusText.textContent = 'ServerSetup Bot is offline';
                showOfflineAlert();
            }
        }
    }
    
    // Start checking bot status
    checkBotStatus();
    
    // Initialize tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === "#") return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Show offline alert
function showOfflineAlert() {
    // Check if alert already exists
    if (document.querySelector('.bot-offline-alert')) {
        return;
    }
    
    const alertContainer = document.createElement('div');
    alertContainer.className = 'alert alert-warning alert-dismissible fade show bot-offline-alert';
    alertContainer.setAttribute('role', 'alert');
    alertContainer.innerHTML = `
        <div class="container">
            <strong>Warning:</strong> The ServerSetup Bot appears to be offline. Some features may not be available.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Insert after the status indicator
    const statusIndicator = document.querySelector('.bot-status');
    if (statusIndicator) {
        statusIndicator.after(alertContainer);
    } else {
        // Fall back to inserting at the top of main content
        const mainContent = document.querySelector('main');
        if (mainContent) {
            mainContent.insertBefore(alertContainer, mainContent.firstChild);
        }
    }
}
const keepAlive = require('./server');
const Monitor = require('ping-monitor');

keepAlive();
const monitor = new Monitor({
    website: '',
    title: 'NAME',
    interval: 2
});

monitor.on('up', (res) => console.log(`${res.website} its on.`));
monitor.on('down', (res) => console.log(`${res.website} it has died - ${res.statusMessage}`));
monitor.on('stop', (website) => console.log(`${website} has stopped.`) );
monitor.on('error', (error) => console.log(error));