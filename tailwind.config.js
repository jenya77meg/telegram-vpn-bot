// /opt/telegram-vpn-bot/tailwind.config.js
const daisyui = require('daisyui').default;
const forms  = require('@tailwindcss/forms');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // где лежат ваши Jinja-шаблоны с классами
    "./volumes/marzban/templates/**/*.html"
  ],
  safelist: [
    // гарантируем генерацию «хардкорных» классов
    "focus:ring-blue-500","focus:border-blue-500",
    "bg-gray-700","border-gray-600","placeholder-gray-400","text-white",
    "btn","card","form-control","p-2.5","rounded-lg","block","w-full",
    "isolate","backdrop-filter","backdrop-blur-md","bg-white/5","border-white/20","p-3"
  ],
  theme: { extend: {} },
  plugins: [
    daisyui,    // стили DaisyUI
    forms       // стили форм
  ],
  daisyui: {
    themes: ["light","dark"]
  },
}
