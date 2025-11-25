db.createCollection("users");
db.users.insertMany([
  { name: "Justin", email: "justin@example.com" },
  { name: "Ana", email: "ana@example.com" }
]);
