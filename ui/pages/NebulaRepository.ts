export class NebulaRepository {

  private cache = new Map<string, Blob>();

  async get(resLevel: number, index: number): Promise<Blob | undefined> {
    const cachedValue = this.cache.get(`${resLevel}/${index}`);
    if (cachedValue !== undefined) {
      return cachedValue;
    }
    try {
      const url = `http://localhost:8000/nebula/${resLevel}/${index}`;
      const response = await fetch(url);
      const blob = await response.blob();
      this.cache.set(`${resLevel}/${index}`, blob);
      return blob;
    }
    catch(_) {
      return undefined;
    }
  }
}