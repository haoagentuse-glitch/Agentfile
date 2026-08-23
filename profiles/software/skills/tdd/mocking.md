# 什麼時候該 mock

只在**系統邊界**上 mock：

- 外部 API（付款、寄信等等）
- 資料庫（有時候——優先用測試用資料庫）
- 時間與亂數
- 檔案系統（有時候）

不要 mock：

- 你自己的類別與模組
- 內部協作者
- 任何你控制得了的東西

## 為了可 mock 而設計

在系統邊界上，把介面設計成容易 mock 的樣子：

**1. 用依賴注入**

外部依賴用傳進來的，不要在內部自己建：

```typescript
// 容易 mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// 難 mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. SDK 風格的介面優於通用取值器**

每個外部操作各給一個明確的函式，不要用一個帶條件判斷的通用函式：

```typescript
// 好：每個函式各自都 mock 得動
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// 壞：mock 內部得寫條件判斷
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

SDK 風格的好處：

- 每個 mock 只回傳一種明確的形狀
- 測試的準備階段不必寫條件判斷
- 一眼看得出這個測試碰到哪些端點
- 每個端點各自有型別保護
