/**
 * Google Calendar Integration for Student Dashboard
 * Handles calendar display, authentication, and event management
 */

class CalendarManager {
    constructor() {
        this.currentDate = new Date();
        this.events = [];
        this.calendarStatus = null;
        this.refreshInterval = null;
        this.isLoading = false;
    }

    /**
     * Initialize the calendar component
     */
    async init() {
        await this.checkCalendarStatus();
        this.renderCalendar();
        this.setupEventListeners();
        
        // Auto-refresh every 5 minutes if user has Google access
        if (this.calendarStatus?.has_google_access) {
            this.startAutoRefresh();
        }
    }

    /**
     * Check user's calendar authentication status
     */
    async checkCalendarStatus() {
        try {
            const response = await fetch('/api/student/me/calendar/status');
            if (response.ok) {
                this.calendarStatus = await response.json();
            } else {
                console.error('Failed to check calendar status');
                this.calendarStatus = { has_google_access: false, auth_method: 'traditional' };
            }
        } catch (error) {
            console.error('Error checking calendar status:', error);
            this.calendarStatus = { has_google_access: false, auth_method: 'traditional' };
        }
    }

    /**
     * Fetch calendar events from Google Calendar
     */
    async fetchCalendarEvents() {
        if (!this.calendarStatus?.has_google_access) {
            return [];
        }

        try {
            this.isLoading = true;
            this.updateLoadingState();

            const response = await fetch('/api/student/me/calendar/events?max_results=50&days_ahead=30');
            
            if (response.ok) {
                const data = await response.json();
                this.events = data.events || [];
                this.showNotification('Calendar events updated', 'success');
                return this.events;
            } else if (response.status === 403) {
                const error = await response.json();
                this.showNotification(error.error || 'Calendar access denied', 'error');
                return [];
            } else {
                throw new Error('Failed to fetch calendar events');
            }
        } catch (error) {
            console.error('Error fetching calendar events:', error);
            this.showNotification('Failed to load calendar events', 'error');
            return [];
        } finally {
            this.isLoading = false;
            this.updateLoadingState();
        }
    }

    /**
     * Render the complete calendar component
     */
    async renderCalendar() {
        const calendarContainer = document.getElementById('calendar-container');
        if (!calendarContainer) return;

        // Fetch events if user has Google access
        if (this.calendarStatus?.has_google_access) {
            await this.fetchCalendarEvents();
        }

        calendarContainer.innerHTML = this.getCalendarHTML();
        this.attachCalendarEventListeners();
    }

    /**
     * Generate calendar HTML based on authentication status
     */
    getCalendarHTML() {
        if (!this.calendarStatus?.has_google_access) {
            return this.getNonGoogleUserHTML();
        }

        return this.getGoogleCalendarHTML();
    }

    /**
     * HTML for non-Google users
     */
    getNonGoogleUserHTML() {
        return `
            <div class="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-lg">
                <div class="text-center py-8">
                    <div class="mb-4">
                        <span class="material-symbols-outlined text-6xl text-gray-400">event</span>
                    </div>
                    <h3 class="text-lg font-semibold mb-2 text-gray-700 dark:text-gray-300">
                        Google Calendar Integration
                    </h3>
                    <p class="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                        To access Google Calendar features, please sign in using your Google account
                    </p>
                    <div class="flex items-center justify-center gap-3">
                        <a href="/api/auth/google/start?role=student" target="_blank" rel="noopener"
                           class="inline-flex items-center gap-2 px-6 py-3 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition-colors text-gray-700 font-medium">
                            <svg class="w-5 h-5" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Sign in with Google
                        </a>
                        <button id="refresh-status" class="px-4 py-3 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">
                            Refresh status
                        </button>
                    </div>
                    <p class="text-xs text-gray-400 mt-3">If the preview blocks Google sign-in, it opens in a new tab.</p>
                </div>
            </div>
        `;
    }

    /**
     * HTML for Google Calendar integration
     */
    getGoogleCalendarHTML() {
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];

        const currentMonth = monthNames[this.currentDate.getMonth()];
        const currentYear = this.currentDate.getFullYear();

        return `
            <div class="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-lg">
                <!-- Calendar Header -->
                <div class="flex justify-between items-center mb-6">
                    <div class="flex items-center gap-3">
                        <h3 class="text-xl font-bold text-gray-900 dark:text-white">
                            ${currentMonth} ${currentYear}
                        </h3>
                        <div id="calendar-loading" class="hidden">
                            <div class="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent"></div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="prev-month" class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">chevron_left</span>
                        </button>
                        <button id="next-month" class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">chevron_right</span>
                        </button>
                        <button id="refresh-calendar" class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ml-2">
                            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">refresh</span>
                        </button>
                    </div>
                </div>

                <!-- Calendar Grid -->
                <div class="grid grid-cols-7 gap-1 mb-4">
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Sun</div>
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Mon</div>
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Tue</div>
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Wed</div>
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Thu</div>
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Fri</div>
                    <div class="text-center text-sm font-medium text-gray-500 dark:text-gray-400 py-2">Sat</div>
                </div>

                <div id="calendar-grid" class="grid grid-cols-7 gap-1">
                    ${this.generateCalendarDays()}
                </div>

                <!-- Upcoming Events Section -->
                <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <h4 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Upcoming Events</h4>
                    <div id="upcoming-events" class="space-y-3">
                        ${this.generateUpcomingEvents()}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate calendar days grid
     */
    generateCalendarDays() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const today = new Date();
        
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay());

        let daysHTML = '';
        const totalDays = 42; // 6 weeks

        for (let i = 0; i < totalDays; i++) {
            const currentDay = new Date(startDate);
            currentDay.setDate(startDate.getDate() + i);
            
            const isCurrentMonth = currentDay.getMonth() === month;
            const isToday = currentDay.toDateString() === today.toDateString();
            const dayEvents = this.getEventsForDate(currentDay);
            
            let dayClasses = 'min-h-[60px] p-2 rounded-lg border border-transparent hover:border-gray-200 dark:hover:border-gray-700 transition-colors cursor-pointer';
            
            if (!isCurrentMonth) {
                dayClasses += ' text-gray-400 dark:text-gray-600';
            } else if (isToday) {
                dayClasses += ' bg-primary text-white font-semibold';
            } else {
                dayClasses += ' text-gray-700 dark:text-gray-300';
            }

            if (dayEvents.length > 0 && isCurrentMonth && !isToday) {
                dayClasses += ' bg-blue-50 dark:bg-blue-900/20';
            }

            daysHTML += `
                <div class="${dayClasses}" data-date="${currentDay.toISOString().split('T')[0]}">
                    <div class="text-sm font-medium">${currentDay.getDate()}</div>
                    ${dayEvents.slice(0, 2).map(event => `
                        <div class="text-xs mt-1 p-1 rounded bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 truncate" title="${this.getEventTitle(event)}">
                            ${this.getEventTitle(event)}
                        </div>
                    `).join('')}
                    ${dayEvents.length > 2 ? `<div class="text-xs text-gray-500 mt-1">+${dayEvents.length - 2} more</div>` : ''}
                </div>
            `;
        }

        return daysHTML;
    }

    /**
     * Generate upcoming events list
     */
    generateUpcomingEvents() {
        if (this.events.length === 0) {
            return `
                <div class="text-center py-4 text-gray-500 dark:text-gray-400">
                    <span class="material-symbols-outlined text-3xl mb-2 block">event_available</span>
                    No upcoming events
                </div>
            `;
        }

        const upcomingEvents = this.events
            .filter(event => {
                const d = this.getEventStartDate(event);
                return d && d >= new Date();
            })
            .slice(0, 5);

        return upcomingEvents.map(event => `
            <div class="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                <div class="flex-shrink-0 w-12 text-center">
                    <div class="text-sm font-semibold text-primary">${this.formatEventDateFromEvent(event)}</div>
                    <div class="text-xs text-gray-500">${this.formatEventTimeFromEvent(event)}</div>
                </div>
                <div class="flex-1 min-w-0">
                    <h5 class="font-medium text-gray-900 dark:text-white truncate">${this.getEventTitle(event)}</h5>
                    ${event.location ? `<p class="text-sm text-gray-500 dark:text-gray-400 truncate">${event.location}</p>` : ''}
                    ${event.description ? `<p class="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">${event.description}</p>` : ''}
                </div>
                ${this.getEventHtmlLink(event) ? `
                    <a href="${this.getEventHtmlLink(event)}" target="_blank" class="flex-shrink-0 p-1 text-gray-400 hover:text-primary transition-colors">
                        <span class="material-symbols-outlined text-sm">open_in_new</span>
                    </a>
                ` : ''}
            </div>
        `).join('');
    }

    /**
     * Get events for a specific date
     */
    getEventsForDate(date) {
        const dateStr = date.toISOString().split('T')[0];
        return this.events.filter(event => {
            const start = this.getEventStartDate(event);
            if (!start) return false;
            const eventDate = start.toISOString().split('T')[0];
            return eventDate === dateStr;
        });
    }

    /**
     * Format event date for display
     */
    formatEventDate(dateStr) {
        const date = new Date(dateStr);
        const month = date.toLocaleDateString('en-US', { month: 'short' });
        const day = date.getDate();
        return `${month} ${day}`;
    }

    /**
     * Format event time for display
     */
    formatEventTime(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }

    /**
     * Helper methods for event data normalization
     */
    getEventTitle(event) {
        return event?.summary || event?.title || 'No Title';
    }

    getEventHtmlLink(event) {
        return event?.htmlLink || event?.html_link || '';
    }

    getEventStartString(event) {
        return event?.start_datetime || event?.start || event?.start?.dateTime || event?.start?.date || null;
    }

    getEventStartDate(event) {
        const s = this.getEventStartString(event);
        if (!s) return null;
        const d = new Date(s);
        return isNaN(d) ? null : d;
    }

    formatEventDateFromEvent(event) {
        const d = this.getEventStartDate(event);
        if (!d) return '—';
        const month = d.toLocaleDateString('en-US', { month: 'short' });
        const day = d.getDate();
        return `${month} ${day}`;
    }

    formatEventTimeFromEvent(event) {
        if (event?.start_time) return event.start_time;
        const d = this.getEventStartDate(event);
        if (!d) return '—';
        return d.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
        });
    }

    /**
     * Setup event listeners for calendar interactions
     */
    setupEventListeners() {
        // Calendar navigation will be attached after rendering
    }

    /**
     * Attach event listeners to calendar elements
     */
    attachCalendarEventListeners() {
        const prevBtn = document.getElementById('prev-month');
        const nextBtn = document.getElementById('next-month');
        const refreshBtn = document.getElementById('refresh-calendar');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.navigateMonth(-1));
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.navigateMonth(1));
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshCalendar());
        }

        // Add click handlers for calendar days
        const calendarDays = document.querySelectorAll('[data-date]');
        calendarDays.forEach(day => {
            day.addEventListener('click', (e) => this.handleDayClick(e));
        });
    }

    /**
     * Navigate to previous/next month
     */
    async navigateMonth(direction) {
        this.currentDate.setMonth(this.currentDate.getMonth() + direction);
        await this.renderCalendar();
    }

    /**
     * Refresh calendar data
     */
    async refreshCalendar() {
        await this.fetchCalendarEvents();
        await this.renderCalendar();
    }

    /**
     * Handle day click events
     */
    handleDayClick(event) {
        const date = event.currentTarget.dataset.date;
        const dayEvents = this.getEventsForDate(new Date(date));
        
        if (dayEvents.length > 0) {
            this.showDayEventsModal(date, dayEvents);
        }
    }

    /**
     * Show modal with events for a specific day
     */
    showDayEventsModal(date, events) {
        const formattedDate = new Date(date).toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });

        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-900 rounded-xl p-6 w-full max-w-md shadow-lg max-h-[80vh] overflow-y-auto">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">${formattedDate}</h3>
                    <button class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800" onclick="this.closest('.fixed').remove()">
                        <span class="material-symbols-outlined text-gray-500">close</span>
                    </button>
                </div>
                <div class="space-y-3">
                    ${events.map(event => `
                        <div class="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                            <h4 class="font-medium text-gray-900 dark:text-white">${this.getEventTitle(event)}</h4>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${this.formatEventTimeFromEvent(event)}</p>
                            ${event.location ? `<p class="text-sm text-gray-600 dark:text-gray-300 mt-1">${event.location}</p>` : ''}
                            ${event.description ? `<p class="text-sm text-gray-600 dark:text-gray-300 mt-2">${event.description}</p>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    /**
     * Update loading state UI
     */
    updateLoadingState() {
        const loadingIndicator = document.getElementById('calendar-loading');
        if (loadingIndicator) {
            loadingIndicator.classList.toggle('hidden', !this.isLoading);
        }
    }

    /**
     * Start auto-refresh for calendar events
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(async () => {
            if (this.calendarStatus?.has_google_access && !this.isLoading) {
                await this.fetchCalendarEvents();
                // Only re-render if we're still on the same month
                const calendarGrid = document.getElementById('calendar-grid');
                if (calendarGrid) {
                    calendarGrid.innerHTML = this.generateCalendarDays();
                    this.attachCalendarEventListeners();
                }
                
                // Update upcoming events
                const upcomingEventsContainer = document.getElementById('upcoming-events');
                if (upcomingEventsContainer) {
                    upcomingEventsContainer.innerHTML = this.generateUpcomingEvents();
                }
            }
        }, 5 * 60 * 1000); // 5 minutes
    }

    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full`;
        
        const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
        notification.className += ` ${bgColor} text-white`;
        
        notification.innerHTML = `
            <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">
                    ${type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info'}
                </span>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);

        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }

    /**
     * Cleanup resources
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Initialize calendar when DOM is loaded
let calendarManager;

document.addEventListener('DOMContentLoaded', function() {
    calendarManager = new CalendarManager();
    calendarManager.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (calendarManager) {
        calendarManager.destroy();
    }
});