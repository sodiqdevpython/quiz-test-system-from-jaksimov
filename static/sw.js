importScripts("https://www.gstatic.com/firebasejs/11.0.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/11.0.1/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyDWFQDDs6xT5phXlKWYoB1YF9WEx8fMRTU",
  authDomain: "test-e56b8.firebaseapp.com",
  projectId: "test-e56b8",
  storageBucket: "test-e56b8.firebasestorage.app",
  messagingSenderId: "572446532812",
  appId: "1:572446532812:web:f9e2e584bc1ec95cf48e69",
  measurementId: "G-66RZYQJ9F8"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log("Background xabar:", payload);

  const { title, body, image, url } = payload.notification;

  self.registration.showNotification(title, {
    body,
    icon: image || "/static/logo.png",
    image: image || undefined,
    data: { url: url || "/" }
  });
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data.url || "/";
  event.waitUntil(clients.openWindow(url));
});


