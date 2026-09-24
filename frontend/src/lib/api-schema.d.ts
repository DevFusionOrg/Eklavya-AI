export interface paths {
  "/health": {
    get: {
      responses: {
        200: { content: { "application/json": { status: string } } };
      };
    };
  };
}
