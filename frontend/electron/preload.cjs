const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  printOrder: (payload) => ipcRenderer.invoke("print:order", payload),
  printTcp: (payload) => ipcRenderer.invoke("print:tcp", payload),
  getApiToken: () => ipcRenderer.invoke("api:getToken"),
});
