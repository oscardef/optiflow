"""
AI-powered analytics service using machine learning algorithms
Includes clustering, forecasting, anomaly detection, and product analysis
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️  scikit-learn not available. Install with: pip install scikit-learn")

from ..models import Product, PurchaseEvent, StockSnapshot, StockLevel, InventoryItem
from ..core import logger


class AIAnalyticsService:
    """AI/ML analytics service for inventory intelligence"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def cluster_products(self, n_clusters: int = 4) -> List[Dict]:
        """
        Enhanced K-means clustering of products based on velocity, stock level, and turnover
        Groups products by similar inventory behavior for strategic insights
        
        Features used:
        - Velocity (sales per day over 30 days)
        - Current stock level
        - Stock-to-sales ratio (inventory efficiency)
        - Price tier
        - Turnover rate
        
        Returns clusters with descriptive labels and actionable insights
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available for clustering")
            return []
        
        # Get products with stock levels
        products_query = self.db.query(Product, StockLevel).join(
            StockLevel, Product.id == StockLevel.product_id, isouter=True
        ).all()
        
        if not products_query:
            logger.info("No products found for clustering")
            return []
        
        # Adjust n_clusters if we have fewer products
        actual_n_clusters = min(n_clusters, len(products_query))
        if actual_n_clusters < 2:
            logger.info(f"Too few products ({len(products_query)}) for clustering")
            return []
        
        features = []
        product_data = []
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        for product, stock_level in products_query:
            # Calculate velocity (sales per day over last 30 days)
            sales_30d = self.db.query(PurchaseEvent).filter(
                PurchaseEvent.product_id == product.id,
                PurchaseEvent.purchased_at >= thirty_days_ago
            ).count()
            velocity = sales_30d / 30.0
            
            # Calculate 7-day velocity for recency
            sales_7d = self.db.query(PurchaseEvent).filter(
                PurchaseEvent.product_id == product.id,
                PurchaseEvent.purchased_at >= seven_days_ago
            ).count()
            velocity_7d = sales_7d / 7.0
            
            # Current stock
            current_stock = stock_level.current_count if stock_level else 0
            
            # Stock-to-sales ratio (inventory efficiency)
            stock_to_sales = current_stock / velocity if velocity > 0 else current_stock
            
            # Turnover rate (how many times inventory is sold)
            turnover_rate = velocity / current_stock if current_stock > 0 else 0
            
            # Price (normalized to avoid scale issues)
            price = float(product.unit_price) if product.unit_price else 0.0
            
            # Features: [velocity, stock, stock_to_sales, turnover, price]
            features.append([velocity, current_stock, stock_to_sales, turnover_rate, price])
            
            product_data.append({
                'product': product,
                'stock_level': stock_level,
                'velocity': velocity,
                'velocity_7d': velocity_7d,
                'current_stock': current_stock,
                'stock_to_sales': stock_to_sales,
                'turnover_rate': turnover_rate,
                'price': price
            })
        
        # Normalize features for better clustering
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Perform K-means clustering
        kmeans = KMeans(n_clusters=actual_n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        # Get cluster centroids in original scale
        centroids = scaler.inverse_transform(kmeans.cluster_centers_)
        
        # Group products by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            data = product_data[i]
            product = data['product']
            
            clusters[int(label)].append({
                'product_id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category,
                'velocity': round(data['velocity'], 2),
                'velocity_7d': round(data['velocity_7d'], 2),
                'stock': data['current_stock'],
                'price': round(data['price'], 2),
                'turnover_rate': round(data['turnover_rate'], 3),
                'stock_to_sales_ratio': round(data['stock_to_sales'], 1)
            })
        
        # Create result with cluster descriptions
        result = []
        for cluster_id, items in clusters.items():
            centroid = centroids[cluster_id]
            
            # Calculate cluster statistics
            velocities = [p['velocity'] for p in items]
            stocks = [p['stock'] for p in items]
            turnovers = [p['turnover_rate'] for p in items]
            prices = [p['price'] for p in items]
            
            avg_velocity = np.mean(velocities)
            avg_stock = np.mean(stocks)
            avg_turnover = np.mean(turnovers)
            avg_price = np.mean(prices)
            
            # Determine cluster characteristics and label
            label, description = self._classify_cluster(
                avg_velocity, avg_stock, avg_turnover, avg_price
            )
            
            result.append({
                'cluster_id': cluster_id,
                'label': label,
                'description': description,
                'size': len(items),
                'avg_velocity': round(avg_velocity, 2),
                'avg_stock': round(avg_stock, 1),
                'avg_turnover': round(avg_turnover, 3),
                'avg_price': round(avg_price, 2),
                'centroid': {
                    'velocity': round(centroid[0], 2),
                    'stock': round(centroid[1], 1),
                    'stock_to_sales': round(centroid[2], 1),
                    'turnover': round(centroid[3], 3),
                    'price': round(centroid[4], 2)
                },
                'products': items[:10]  # Limit to top 10 products per cluster for performance
            })
        
        # Sort by velocity descending
        result.sort(key=lambda x: x['avg_velocity'], reverse=True)
        
        return result
    
    def _classify_cluster(self, velocity: float, stock: float, turnover: float, price: float) -> Tuple[str, str]:
        """
        Classify cluster based on characteristics and provide actionable label
        
        Returns: (label, description)
        """
        # High velocity, high turnover = Best sellers
        if velocity > 2 and turnover > 0.1:
            return "Fast Movers", "High velocity products with strong turnover - maintain stock levels"
        
        # Low velocity, high stock = Slow movers
        elif velocity < 0.5 and stock > 20:
            return "Slow Movers", "Low velocity with excess stock - consider promotions"
        
        # High stock, low turnover = Dead stock risk
        elif stock > 30 and turnover < 0.05:
            return "Dead Stock Risk", "High inventory with minimal turnover - review pricing/placement"
        
        # Moderate velocity, balanced stock = Steady sellers
        elif 0.5 <= velocity <= 2 and 10 <= stock <= 30:
            return "Steady Sellers", "Consistent velocity with balanced inventory - maintain strategy"
        
        # Low stock, moderate velocity = Restock priority
        elif stock < 10 and velocity > 0.5:
            return "Restock Priority", "Good velocity but low stock - prioritize restocking"
        
        # High price items
        elif price > 50:
            return "Premium Products", "Higher-priced items requiring careful inventory management"
        
        # Default
        else:
            return "Mixed Category", "Diverse product mix with varied characteristics"
    
    def forecast_demand(self, product_id: int, days_ahead: int = 7) -> Dict:
        """
        Simple exponential smoothing forecast for product demand
        Returns predicted sales for next N days
        """
        # Get historical sales data
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        purchases = self.db.query(
            func.date(PurchaseEvent.purchased_at).label('date'),
            func.count(PurchaseEvent.id).label('count')
        ).filter(
            PurchaseEvent.product_id == product_id,
            PurchaseEvent.purchased_at >= thirty_days_ago
        ).group_by(func.date(PurchaseEvent.purchased_at)).all()
        
        if len(purchases) < 3:
            return {
                'product_id': product_id,
                'forecast': [],
                'confidence': 'low',
                'message': 'Insufficient historical data'
            }
        
        # Extract daily counts
        daily_sales = [p.count for p in purchases]
        
        # Simple exponential smoothing with alpha=0.3
        alpha = 0.3
        forecast = []
        last_value = daily_sales[-1]
        
        for i in range(days_ahead):
            # Exponential smoothing prediction
            if len(daily_sales) > 0:
                smoothed = alpha * last_value + (1 - alpha) * np.mean(daily_sales[-7:])
            else:
                smoothed = last_value
            
            forecast.append(max(0, round(smoothed, 1)))
            last_value = smoothed
        
        # Calculate confidence based on variance
        variance = np.var(daily_sales) if len(daily_sales) > 1 else 0
        confidence = 'high' if variance < 5 else 'medium' if variance < 15 else 'low'
        
        return {
            'product_id': product_id,
            'forecast': forecast,
            'average_daily_sales': round(np.mean(daily_sales), 2),
            'confidence': confidence,
            'historical_variance': round(variance, 2)
        }
    
    def detect_anomalies(self, lookback_days: int = 7) -> List[Dict]:
        """
        Detect unusual stock movements using Z-score analysis
        Returns products with anomalous behavior
        """
        anomalies = []
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get all products with recent activity
        products = self.db.query(Product).all()
        
        for product in products:
            # Get recent sales
            recent_sales = self.db.query(PurchaseEvent).filter(
                PurchaseEvent.product_id == product.id,
                PurchaseEvent.purchased_at >= cutoff_date
            ).count()
            
            # Get historical average (30 days ago to 7 days ago)
            hist_start = datetime.utcnow() - timedelta(days=30)
            hist_end = datetime.utcnow() - timedelta(days=lookback_days)
            
            historical_sales = self.db.query(PurchaseEvent).filter(
                PurchaseEvent.product_id == product.id,
                PurchaseEvent.purchased_at >= hist_start,
                PurchaseEvent.purchased_at < hist_end
            ).count()
            
            historical_avg = historical_sales / (30 - lookback_days)
            
            if historical_avg == 0 and recent_sales == 0:
                continue
            
            # Calculate Z-score
            if historical_avg > 0:
                z_score = (recent_sales / lookback_days - historical_avg) / (historical_avg + 0.01)
            else:
                z_score = recent_sales  # First-time sales
            
            # Flag if unusual (z-score > 2 or < -2)
            if abs(z_score) > 2:
                anomaly_type = 'spike' if z_score > 0 else 'drop'
                severity = 'high' if abs(z_score) > 3 else 'medium'
                
                anomalies.append({
                    'product_id': product.id,
                    'sku': product.sku,
                    'name': product.name,
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'z_score': round(z_score, 2),
                    'recent_sales': recent_sales,
                    'expected_sales': round(historical_avg * lookback_days, 1),
                    'detected_at': datetime.utcnow().isoformat()
                })
        
        return sorted(anomalies, key=lambda x: abs(x['z_score']), reverse=True)
    
    def abc_analysis(self) -> Dict[str, List[Dict]]:
        """
        ABC classification based on revenue contribution
        A = top 20% by value, B = next 30%, C = remaining 50%
        """
        # Calculate revenue per product
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        product_revenues = []
        products = self.db.query(Product).all()
        
        for product in products:
            sales_count = self.db.query(PurchaseEvent).filter(
                PurchaseEvent.product_id == product.id,
                PurchaseEvent.purchased_at >= thirty_days_ago
            ).count()
            
            revenue = sales_count * float(product.unit_price if product.unit_price else 0)
            
            stock = self.db.query(StockLevel).filter(
                StockLevel.product_id == product.id
            ).first()
            
            product_revenues.append({
                'product_id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category,
                'revenue': revenue,
                'sales_count': sales_count,
                'current_stock': stock.current_count if stock else 0
            })
        
        # Sort by revenue
        product_revenues.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Calculate cumulative percentage
        total_revenue = sum(p['revenue'] for p in product_revenues)
        cumulative = 0
        
        classification = {'A': [], 'B': [], 'C': []}
        
        for product in product_revenues:
            cumulative += product['revenue']
            cumulative_pct = (cumulative / total_revenue * 100) if total_revenue > 0 else 0
            
            if cumulative_pct <= 70:
                classification['A'].append(product)
            elif cumulative_pct <= 90:
                classification['B'].append(product)
            else:
                classification['C'].append(product)
        
        return classification
    
    def product_affinity(self, min_support: float = 0.05) -> List[Dict]:
        """
        Find products frequently purchased together
        Simple association rule mining
        """
        # Get recent purchases grouped by time proximity (within 1 hour = same basket)
        one_hour = timedelta(hours=1)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        purchases = self.db.query(PurchaseEvent).filter(
            PurchaseEvent.purchased_at >= thirty_days_ago
        ).order_by(PurchaseEvent.purchased_at).all()
        
        # Group into baskets
        baskets = []
        current_basket = set()
        last_time = None
        
        for purchase in purchases:
            if last_time and (purchase.purchased_at - last_time) > one_hour:
                if current_basket:
                    baskets.append(current_basket)
                current_basket = set()
            
            current_basket.add(purchase.product_id)
            last_time = purchase.purchased_at
        
        if current_basket:
            baskets.append(current_basket)
        
        # Find frequent pairs
        pair_counts = defaultdict(int)
        total_baskets = len(baskets)
        
        for basket in baskets:
            items = list(basket)
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    pair = tuple(sorted([items[i], items[j]]))
                    pair_counts[pair] += 1
        
        # Filter by minimum support
        min_count = int(total_baskets * min_support)
        frequent_pairs = []
        
        for (prod1_id, prod2_id), count in pair_counts.items():
            if count >= min_count:
                support = count / total_baskets
                
                # Get product names
                prod1 = self.db.query(Product).filter(Product.id == prod1_id).first()
                prod2 = self.db.query(Product).filter(Product.id == prod2_id).first()
                
                if prod1 and prod2:
                    frequent_pairs.append({
                        'product1_id': prod1_id,
                        'product1_name': prod1.name,
                        'product2_id': prod2_id,
                        'product2_name': prod2.name,
                        'frequency': count,
                        'support': round(support, 3),
                        'confidence': round(count / max(1, total_baskets), 3)
                    })
        
        return sorted(frequent_pairs, key=lambda x: x['frequency'], reverse=True)
