from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict
from abc import ABC, abstractmethod

# ==========================================
# 1. PATRÓN ESTRATEGIA (Cálculo de Precios)
# ==========================================
class PricingStrategy(ABC):
    @abstractmethod
    def calculate_total(self, unit_price: float, quantity: float) -> float:
        pass

class NormalPricing(PricingStrategy):
    def calculate_total(self, unit_price: float, quantity: float) -> float:
        return unit_price * quantity

class WeightPricing(PricingStrategy):
    def calculate_total(self, unit_price: float, quantity: float) -> float:
        # Precio dado por gramo, se calcula por kilogramo
        precio_por_kilo = unit_price * 1000
        return precio_por_kilo * quantity

class SpecialPricing(PricingStrategy):
    def calculate_total(self, unit_price: float, quantity: float) -> float:
        # 20% descuento por cada 3 unidades, máximo 50%
        grupos_de_tres = int(quantity // 3)
        descuento_porcentaje = min(50.0, grupos_de_tres * 20.0)
        factor_pago = 1.0 - (descuento_porcentaje / 100.0)
        return (unit_price * quantity) * factor_pago

class PricingFactory:
    @staticmethod
    def get_strategy(sku: str) -> PricingStrategy:
        if sku.startswith("EA"): return NormalPricing()
        if sku.startswith("WE"): return WeightPricing()
        if sku.startswith("SP"): return SpecialPricing()
        return NormalPricing()

# ==========================================
# 2. MODELOS DE DOMINIO (Entidades)
# ==========================================
class Product:
    def __init__(self, sku: str, name: str, desc: str, stock: float, price: float):
        self.sku = sku
        self.name = name
        self.description = desc
        self.stock = stock
        self.unit_price = price
        self.pricing_strategy = PricingFactory.get_strategy(sku)
        
    def calculate_price(self, quantity: float) -> float:
        return self.pricing_strategy.calculate_total(self.unit_price, quantity)

class CartItem:
    def __init__(self, product: Product, quantity: float):
        self.product = product
        self.quantity = quantity
        self.total = product.calculate_price(quantity)

class Store:
    def __init__(self):
        self.inventory: Dict[str, Product] = {}
        self.cart: Dict[str, CartItem] = {}
        self.total_sales: float = 0.0

    def add_product_to_inventory(self, product: Product):
        self.inventory[product.sku] = product

    def add_to_cart(self, sku: str, quantity: float):
        if sku not in self.inventory:
            raise ValueError("Producto no encontrado")
        
        product = self.inventory[sku]
        current_cart_qty = self.cart[sku].quantity if sku in self.cart else 0
        
        if product.stock < (current_cart_qty + quantity):
            raise ValueError("Stock insuficiente")
            
        self.cart[sku] = CartItem(product, current_cart_qty + quantity)

    def remove_from_cart(self, sku: str):
        if sku in self.cart:
            del self.cart[sku]

    def checkout(self):
        sale_total = sum(item.total for item in self.cart.values())
        for sku, item in self.cart.items():
            self.inventory[sku].stock -= item.quantity
        self.total_sales += sale_total
        self.cart.clear()
        return sale_total

# ==========================================
# 3. CAPA WEB (FastAPI - Backend)
# ==========================================
app = FastAPI()
store = Store()

# Poblar inventario inicial
store.add_product_to_inventory(Product("EA-01", "Camiseta", "Camiseta normal", 50, 20000))
store.add_product_to_inventory(Product("WE-01", "Manzana", "Precio por gramo", 10, 5))
store.add_product_to_inventory(Product("SP-01", "Audífonos", "Descuento volumen", 20, 50000))

class CartRequest(BaseModel):
    sku: str
    quantity: float

@app.get("/products")
def get_products():
    return [{"sku": p.sku, "name": p.name, "stock": p.stock, "price": p.unit_price} for p in store.inventory.values()]

@app.get("/cart")
def get_cart():
    items = [{"sku": i.product.sku, "name": i.product.name, "quantity": i.quantity, "total": i.total} for i in store.cart.values()]
    total_compra = sum(i["total"] for i in items)
    return {"items": items, "total_compra": total_compra}

@app.post("/cart")
def add_item(req: CartRequest):
    try:
        store.add_to_cart(req.sku, req.quantity)
        return {"msg": "Agregado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/cart/{sku}")
def remove_item(sku: str):
    store.remove_from_cart(sku)
    return {"msg": "Eliminado"}

@app.post("/checkout")
def checkout():
    total = store.checkout()
    return {"msg": f"Compra exitosa por ${total}", "ventas_acumuladas": store.total_sales}

# ==========================================
# 4. CAPA FRONTEND (Interfaz Gráfica)
# ==========================================
html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Tienda POO</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background-color: #f4f7f6; color: #333; }
        .container { display: flex; gap: 20px; max-width: 900px; margin: 0 auto; }
        .panel { background: white; padding: 20px; width: 50%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #2c3e50; }
        .item { border-bottom: 1px solid #eee; padding: 10px 0; display: flex; justify-content: space-between; align-items: center; }
        .item-info { flex-grow: 1; }
        .controls { display: flex; gap: 10px; align-items: center; }
        input[type="number"] { width: 60px; padding: 5px; border: 1px solid #ccc; border-radius: 4px; }
        button { background-color: #3498db; color: white; border: none; padding: 8px 12px; cursor: pointer; border-radius: 4px; font-weight: bold; }
        button:hover { background-color: #2980b9; }
        button.danger { background-color: #e74c3c; }
        button.danger:hover { background-color: #c0392b; }
        button.success { background-color: #2ecc71; width: 100%; margin-top: 15px; font-size: 16px; padding: 12px; }
        button.success:hover { background-color: #27ae60; }
        .total-box { margin-top: 20px; padding-top: 15px; border-top: 2px solid #eee; text-align: right; }
    </style>
</head>
<body>
    <h1>🛒 Mi Tienda Web - Caso POO</h1>
    <div class="container">
        <!-- Panel de Inventario -->
        <div class="panel">
            <h2 style="color: #2980b9;">📦 Inventario</h2>
            <div id="products-list"></div>
        </div>
        
        <!-- Panel de Carrito -->
        <div class="panel">
            <h2 style="color: #27ae60;">🛍️ Carrito de Compras</h2>
            <div id="cart-list"></div>
            <div class="total-box">
                <h3 id="cart-total">Total Compra: $0</h3>
                <button class="success" onclick="checkout()">Finalizar Compra</button>
            </div>
        </div>
    </div>

    <script>
        async function loadProducts() {
            const res = await fetch('/products');
            const data = await res.json();
            const list = document.getElementById('products-list');
            list.innerHTML = data.map(p => `
                <div class="item">
                    <div class="item-info">
                        <strong>${p.name}</strong> <small>(${p.sku})</small><br>
                        Precio base: $${p.price} | Stock: ${p.stock}
                    </div>
                    <div class="controls">
                        <input type="number" id="qty-${p.sku}" value="1" min="1" step="0.5">
                        <button onclick="addToCart('${p.sku}')">Agregar</button>
                    </div>
                </div>
            `).join('');
        }

        async function loadCart() {
            const res = await fetch('/cart');
            const data = await res.json();
            const list = document.getElementById('cart-list');
            
            if(data.items.length === 0) {
                list.innerHTML = "<p style='color: #7f8c8d; text-align: center;'>El carrito está vacío</p>";
            } else {
                list.innerHTML = data.items.map(i => `
                    <div class="item">
                        <div class="item-info">
                            <strong>${i.name}</strong><br>
                            Cant: ${i.quantity} | Subtotal: $${i.total}
                        </div>
                        <button class="danger" onclick="removeFromCart('${i.sku}')">Quitar</button>
                    </div>
                `).join('');
            }
            document.getElementById('cart-total').innerText = `Total Compra: $${data.total_compra}`;
        }

        async function addToCart(sku) {
            const qtyInput = document.getElementById(`qty-${sku}`);
            const qty = parseFloat(qtyInput.value);
            
            const res = await fetch('/cart', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sku: sku, quantity: qty})
            });
            
            if(res.ok) {
                loadCart();
                qtyInput.value = 1; 
            } else {
                const err = await res.json();
                alert("Error: " + err.detail);
            }
        }

        async function removeFromCart(sku) {
            await fetch(`/cart/${sku}`, { method: 'DELETE' });
            loadCart();
        }

        async function checkout() {
            const res = await fetch('/checkout', { method: 'POST' });
            const data = await res.json();
            if(res.ok && data.msg.includes("$0.0") === false) {
                alert("🎉 " + data.msg + "\\n\\nVentas acumuladas de la tienda: $" + data.ventas_acumuladas);
                loadProducts(); 
                loadCart();     
            } else {
                alert("Agrega productos al carrito primero.");
            }
        }

        loadProducts();
        loadCart();
    </script>
</body>
</html>
"""

@app.get("/site", response_class=HTMLResponse)
def serve_frontend():
    return html_content