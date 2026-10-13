import pandas as pd
from sqlalchemy.orm import Session
from mlxtend.frequent_patterns import apriori, association_rules
import models

def get_market_basket_analysis(db: Session, min_support: float = 0.1, min_confidence: float = 0.5):
    # 1. ดึงข้อมูลรายการสินค้าในบิลทั้งหมดจากฐานข้อมูล
    query = db.query(
        models.SaleItem.sale_id,
        models.Product.product_name,
        models.SaleItem.quantity
    ).join(models.Product, models.SaleItem.product_id == models.Product.product_id)
    
    df = pd.read_sql(query.statement, db.bind)

    if df.empty or len(df['sale_id'].unique()) < 2:
        return {"status": "warning", "message": "ข้อมูลประวัติการขายยังมีไม่เพียงพอสำหรับการวิเคราะห์ (ต้องมีอย่างน้อย 2 บิลขึ้นไป)"}

    # 2. แปลงข้อมูลให้อยู่ในรูป Basket Matrix (One-Hot Encoding)
    basket = (df.groupby(['sale_id', 'product_name'])['quantity']
              .sum().unstack().reset_index().fillna(0)
              .set_index('sale_id'))

    # แปลงจำนวนสินค้าให้เป็น True/False (1 หรือ 0)
    def encode_units(x):
        return x > 0

    basket_sets = basket.map(encode_units)

    # 3. คำนวณหา Frequent Itemsets ด้วย Apriori Algorithm
    frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)

    if frequent_itemsets.empty:
        return {"status": "success", "rules": [], "message": "ไม่พบรูปแบบสินค้าที่ซื้อร่วมกันตามเงื่อนไข Support ที่กำหนด"}

    # 4. สร้าง Association Rules
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)

    # 5. จัดรูปแบบผลลัพธ์ส่งกลับ
    results = []
    for _, row in rules.iterrows():
        results.append({
            "antecedents": list(row['antecedents']),
            "consequents": list(row['consequents']),
            "support": round(float(row['support']), 4),
            "confidence": round(float(row['confidence']), 4),
            "lift": round(float(row['lift']), 4)
        })

    return {
        "status": "success",
        "total_rules": len(results),
        "rules": results
    }
