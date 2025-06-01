// Обработчик клика по иконке расширения
chrome.action.onClicked.addListener((tab) => {
  // Открываем боковую панель
  chrome.sidePanel.open({ windowId: tab.windowId });
}); 