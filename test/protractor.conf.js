exports.config = {
    seleniumAddress: 'http://localhost:4444/wd/hub',
    specs: ['e2e/**/*.js'],
    baseUrl: 'http://localhost:8080' //default test port with Yeoman
};
