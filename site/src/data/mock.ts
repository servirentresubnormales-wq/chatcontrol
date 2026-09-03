export interface Streamer {
  id: string;
  displayName: string;
  twitchUsername: string;
  twitchConnected: boolean;
  minecraftUsername: string;
  minecraftConnected: boolean;
}

export interface EventConfig {
  id: number;
  name: string;
  action: string;
  enabled: boolean;
  cooldown: number;
  params: Record<string, number | string>;
}

export const mockStreamer: Streamer = {
  id: '12345678',
  displayName: 'DemoStreamer',
  twitchUsername: 'demostreamer',
  twitchConnected: true,
  minecraftUsername: 'DemoStreamer',
  minecraftConnected: true,
};

export const mockEvents: EventConfig[] = [
  { id: 1, name: 'Zombie', action: 'zombie', enabled: true, cooldown: 10, params: { count: 3, radius: 5 } },
  { id: 2, name: 'Arañas', action: 'spiders', enabled: true, cooldown: 10, params: { count: 2, radius: 5 } },
  { id: 3, name: 'Lentitud', action: 'slowness', enabled: true, cooldown: 15, params: { duration: 10, amplifier: 1 } },
  { id: 4, name: 'Ceguera', action: 'blindness', enabled: true, cooldown: 15, params: { duration: 8, amplifier: 1 } },
  { id: 5, name: 'Creeper', action: 'creeper', enabled: true, cooldown: 30, params: { count: 1, radius: 3 } },
  { id: 6, name: 'Tormenta', action: 'storm', enabled: true, cooldown: 60, params: { duration: 60, thunder: true } },
  { id: 7, name: 'Teletransporte', action: 'random_teleport', enabled: true, cooldown: 20, params: { radius: 100 } },
  { id: 8, name: 'Explosión', action: 'explosion', enabled: true, cooldown: 30, params: { power: 4, radius: 10 } },
  { id: 9, name: 'Evento Random', action: 'random_event', enabled: true, cooldown: 45, params: {} },
  { id: 10, name: 'Pollos', action: 'chickens', enabled: true, cooldown: 0, params: { count: 10, radius: 5 } },
];
