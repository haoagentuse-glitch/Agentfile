# 好測試與壞測試

## 好測試

**整合風格**：透過真實介面測，不去 mock 內部零件。

```typescript
// 好：測的是觀察得到的行為
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

特徵：

- 測的是使用者／呼叫端在乎的行為
- 只用公開 API
- 撐得過內部重構
- 描述**做到什麼**，不描述**怎麼做**
- 一個測試一個邏輯斷言

## 壞測試

**測實作細節**：跟內部結構耦合。

```typescript
// 壞：測的是實作細節
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

警訊：

- mock 內部協作者
- 測私有方法
- 對呼叫次數或呼叫順序下斷言
- 行為沒變、只是重構，測試就壞了
- 測試名稱描述的是**怎麼做**而不是**做到什麼**
- 繞過介面、從外部手段驗證

```typescript
// 壞：繞過介面去驗證
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// 好：透過介面驗證
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

**同義反覆的測試**：期望值把實作重講一遍，於是測試天生就會通過。

```typescript
// 壞：期望值用程式碼自己的算法重算一次
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// 好：期望值是獨立、已知的字面值
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```
