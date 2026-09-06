const STORAGE_KEY = 'lm_user';

export const authService = {
  /** Get the persisted user from localStorage */
  getUser() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    } catch {
      return null;
    }
  },

  /** Persist user to localStorage */
  setUser(user) {
    if (user) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  },

  /** Clear session */
  logout() {
    localStorage.removeItem(STORAGE_KEY);
  },

  /** Check if a user is stored */
  isAuthenticated() {
    return this.getUser() !== null;
  },
};
