const routes: Record<string, () => Promise<void>> = {
  '/register': async () => {
    await import('./register');
    document.getElementById('app')!.innerHTML = '<register-view></register-view>';
  }
};

export const handleNavigation = async () => {
  //URLのドメインより後ろを取得
  const path = window.location.pathname;
  const routeAction = routes[path] || routes['/register'];
  if (routeAction) {
    await routeAction();
  }
};