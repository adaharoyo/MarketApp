# 🌱 Market Hub — Farm-to-Table Marketplace

> **Connect local farmers directly with buyers. Fresh produce, zero middlemen.**

![Django](https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Phase%203%20Complete-f3b61f?style=flat-square)

---

## 📖 Overview

Market Hub is a full-stack Django web application that bridges the gap between local farmers and buyers. Farmers list fresh produce with pricing, harvest dates, and stock levels. Buyers browse, add to cart, checkout, and track their order through a live status pipeline — from Pending to Delivered.

---

## 🎨 Design Palette

| Name | Hex | Role |
|---|---|---|
| Black Cherry | `#510d0a` | Primary — navbar, buttons, headings |
| Sunflower Gold | `#f3b61f` | Accent — CTAs, highlights |
| Celadon | `#bbd8b3` | Secondary — backgrounds, table headers |
| Old Gold | `#a29f15` | Stars, category badges, status labels |
| Pitch Black | `#191102` | Body text, prices |

---

## ✨ Features

### 🛍 Marketplace (Public — no login required)
- Browse all available produce
- **Search** by crop name or description
- **Filter** by category, farmer, price range
- **Freshness badges** — colour-coded from harvest date (🟢 today / 🟡 2 days / 🔴 older)
- **Star ratings** displayed on product cards
- "Login to Buy" prompt for guests

### 🌾 For Farmers
- Register as a farmer with contact & location
- **Add products** — with category, unit (kg/bunch/litre…), currency, harvest date, image
- **Multi-currency support** — UGX (default), KES, TZS, USD, EUR, GBP
- **Dashboard** with quick stats — today's orders, today's revenue, low-stock alerts
- **Order management** — Confirm → Preparing → Ready → Deliver (Direct button)
- **Earnings page** — All-time / monthly / weekly / daily revenue + best-selling products
- **In-app notifications** for every new order

### 🛒 For Buyers (Clients)
- **Session-based cart** — works before login; cart persists across pages
- **Cart grouped by farmer** — clear multi-seller view with stock warnings
- **Step-based checkout** — Pickup or Home Delivery with address toggle
- **Mock Payment** — Orders are automatically paid via a mock system during checkout
- **DPoD box** — "Pay on Delivery" explanation for trust building
- **Order tracking** — 5-step progress bar (Pending → Confirmed → Preparing → Ready → Delivered)
- **Status notifications** — real-time in-app alerts on every order update

### 🔔 Global UI
- **Toast notifications** — floating auto-dismiss messages for every action
- **Notification bell** dropdown in navbar — latest 5 alerts, mark-all-read
- **Cart badge** — live item count in navbar
- **Mobile bottom nav** — Home / Shop / Cart / Dashboard fixed bar on phones
- **Product ratings & reviews** — star input + text; one review per buyer per product

---

## 🗂 Project Structure

```
MarketApp/
├── farmermarket/              # Django project config
│   ├── settings.py            # Theme, DB, media config
│   ├── urls.py                # Master URL routing
│   └── wsgi.py
│
├── farmersmarket/             # Main application
│   ├── models.py              # All data models
│   ├── views.py               # All view logic
│   ├── forms.py               # ModelForms
│   ├── context_processors.py  # Cart count, notif count, theme — global
│   ├── migrations/
│   └── templates/
│       ├── base.html          # Master layout (toast, bell, mobile nav)
│       ├── home.html          # Landing page
│       ├── marketplace.html   # Product grid + filters
│       ├── product_detail.html# Single product + reviews
│       ├── cart.html          # Cart grouped by farmer
│       ├── checkout.html      # Step checkout + DPoD
│       ├── order_detail.html  # Progress tracker
│       ├── farmer_dashboard.html
│       ├── farmer_earnings.html
│       ├── client_dashboard.html
│       ├── login.html
│       ├── register.html
│       └── generic_form.html
│
├── media/                     # Uploaded product images
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🗃 Data Models

```
Farmer ──────────────── User (OneToOne)
Farm   ──────────────── Farmer (FK)

Client ──────────────── User (OneToOne)

Product
  ├── farmer (FK)
  ├── category (choices)
  ├── unit    (choices)
  ├── currency (choices, default UGX)
  ├── harvest_date → freshness_label property
  └── avg_rating / rating_count properties

ProductRating
  ├── product (FK)
  ├── client  (FK)
  ├── stars   (1–5)
  └── unique_together = (product, client)

Order
  ├── client (FK)
  ├── status: Pending → Confirmed → Preparing → Ready → Delivered | Cancelled
  └── delivery_type: Pickup | Delivery

OrderItem   ── Order (FK) + Product (FK)
Payment     ── Order (FK)  ← Mock payment record created on checkout
Notification── Farmer|Client (FK)
```

---

## 🔄 Order State Machine

```
Pending ──→ Confirmed ──→ Preparing ──→ Ready ──→ Delivered
   └──────────────────────────────────────→ Cancelled
```

Farmers manage the order flow directly from their dashboard. Once an order is "Ready", the farmer can mark it as "Delivered" with a single click.

---

## 🚀 Quick Start

### 1. Clone & setup environment

```bash
git clone <repo-url>
cd MarketApp
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. (Optional) Create admin superuser

```bash
python manage.py createsuperuser
```

### 5. Run

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000**

---

## 🌐 URL Reference

| Method | Path | Description |
|---|---|---|
| GET | `/` | Home — featured products |
| GET | `/marketplace/` | Full product browse & filter |
| GET | `/marketplace/<id>/` | Product detail + reviews |
| POST | `/marketplace/<id>/rate/` | Submit star rating |
| GET/POST | `/login/` | Login |
| GET/POST | `/register/` | Register (farmer or client) |
| GET | `/logout/` | Logout + clear cart |
| GET | `/dashboard/` | Auto-routed dashboard |
| GET | `/earnings/` | Farmer revenue analytics |
| GET | `/cart/` | View cart |
| POST | `/cart/add/<id>/` | Add to cart |
| POST | `/cart/remove/<id>/` | Remove item |
| POST | `/cart/update/<id>/` | Update quantity |
| GET/POST | `/checkout/` | Checkout & place order |
| GET | `/orders/<id>/` | Order detail + tracker |
| POST | `/orders/<id>/status/` | Advance order status (farmer) |
| POST | `/notifications/read/` | Mark all notifications read |
| GET/POST | `/add_product/` | Add product (farmer only) |

---

## ⚙️ Configuration

### Theme (`farmermarket/settings.py`)

```python
THEME_CONFIG = {
    'PRIMARY_COLOR':   '#510d0a',   # Black Cherry
    'SECONDARY_COLOR': '#bbd8b3',   # Celadon
    'ACCENT_COLOR':    '#f3b61f',   # Sunflower Gold
    'GOLD_COLOR':      '#a29f15',   # Old Gold
    'DARK_COLOR':      '#191102',   # Pitch Black
}
```

### Media files

```python
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

## 📦 Requirements

```
Django>=5.0
Pillow
```

---

## 🗺 Roadmap

| Phase | Status | Features |
|---|---|---|
| Phase 1 | ✅ Done | Models, auth, basic templates |
| Phase 2 | ✅ Done | Cart, checkout, order status, notifications, search, currency |
| Phase 3 | ✅ Done | Ratings, Mock Payments, earnings analytics, freshness badges, categories, toast UI, mobile nav |
| Phase 4 | 🔜 Next | Real Payment gateway, logistics/rider module, subscriptions, charts, PWA push notifications |

---

## 🤝 User Roles

### Farmer
- Dashboard, Add Product, Earnings, Order management (Direct status updates)

### Client (Buyer)
- Marketplace, Cart, Checkout (Mock Payment), Order tracking, Reviews

---

*Built with Django · Designed for African farm markets · Phase 3 Complete*
