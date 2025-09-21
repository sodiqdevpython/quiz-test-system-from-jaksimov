importScripts("https://www.gstatic.com/firebasejs/11.0.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/11.0.1/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyAd2vyJI_dNy1D0mmPTkRB4u1Tqz-KVylc",
  authDomain: "notify-89a18.firebaseapp.com",
  projectId: "notify-89a18",
  storageBucket: "notify-89a18.firebasestorage.com",
  messagingSenderId: "197374439129",
  appId: "1:197374439129:web:ea78742dbb9bc3af2218c8"
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


