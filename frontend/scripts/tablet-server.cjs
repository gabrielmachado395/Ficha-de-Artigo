const path = require("path");
const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();

const distDir = path.join(__dirname, "..", "dist-web");
const backendUrl = process.env.BACKEND_URL || "http://168.190.90.2:5000";
const port = Number(process.env.PORT || 8080);

app.use(
  "/api",
  createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    ws: true,
    pathRewrite: {
      "^/api": "",
    },
  })
);

app.use(express.static(distDir));

// SPA fallback
app.get("*", (_req, res) => {
  res.sendFile(path.join(distDir, "index.html"));
});

app.listen(port, "0.0.0.0", () => {
  console.log("Tablet server online");
  console.log(`- dist: ${distDir}`);
  console.log(`- backend: ${backendUrl}`);
  console.log(`- url: http://SEU_IP_DO_PC:${port}`);
});
