"""Support for Bosch home thermostats."""

import logging

from .const import DOMAIN, SENSOR_TYPES
from .nefit_entity import NefitEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Sensor platform setup for nefit easy."""
    entities = []

    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    data = config_entry.data

    for key in SENSOR_TYPES:
        typeconf = SENSOR_TYPES[key]
        if key == "status":
            entities.append(NefitStatus(client, data, key, typeconf))
        elif key == "cause":
            entities.append(NefitCause(client, data, key, typeconf))
        elif key == "year_total":
            entities.append(NefitYearTotal(client, data, key, typeconf))
        else:
            entities.append(NefitSensor(client, data, key, typeconf))

    async_add_entities(entities, True)


class NefitSensor(NefitEntity):
    """Representation of a NefitSensor entity."""

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if "device_class" in self._typeconf:
            return self._typeconf["device_class"]

        return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        if "unit" in self._typeconf:
            return self._typeconf["unit"]

        return None


class NefitYearTotal(NefitSensor):
    """Representation of the total year consumption."""

    @property
    def state(self):
        """Return the state/value of the sensor."""
        data = self.coordinator.data.get(self._key)

        if data is None:
            return None

        return "{:.1f}".format(
            data * 0.12307692
        )  # convert kWh to m3, for LPG, multiply with 0.040742416


class NefitStatus(NefitSensor):
    """Representation of the boiler status."""

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return get_status(self.coordinator.data.get(self._key))


def get_status(code):
    """Return status of sensor."""
    display_codes = {
        "-H": "-H: central heating active",
        "=H": "=H: hot water active",
        "0C": "0C: system starting",
        "0L": "0L: system starting",
        "0U": "0U: system starting",
        "0E": "0E: system waiting",
        "0H": "0H: system standby",
        "0A": "0A: system waiting (boiler cannot transfer heat to central heating)",
        "0Y": "0Y: system waiting (boiler cannot transfer heat to central heating)",
        "2E": "2E: boiler water pressure too low",
        "H07": "H07: boiler water pressure too low",
        "2F": "2F: sensors measured abnormal temperature",
        "2L": "2L: sensors measured abnormal temperature",
        "2P": "2P: sensors measured abnormal temperature",
        "2U": "2U: sensors measured abnormal temperature",
        "4F": "4F: sensors measured abnormal temperature",
        "4L": "4L: sensors measured abnormal temperature",
        "6A": "6A: burner doesn't ignite",
        "6C": "6C: burner doesn't ignite",
        "rE": "rE: system restarting",
    }
    if code in display_codes:
        return display_codes[code]

    return code

class NefitCause(NefitSensor):
    """Representation of the boiler cause."""

    @property
    def state(self):
        """Return the cause/value of the sensor."""
        return get_cause(self.coordinator.data.get(self._key))


def get_cause(code):
    """Return cause of sensor."""
    cause_codes = {
        208: "208: Het cv-toestel bevindt zich in schoorsteenvegerbedrijf of in servicebedrijf.",
        200: "200: Het cv-toestel bevindt zich in cv-bedrijf.",
        201: "201: Het cv-toestel bevindt zich in warmwaterbedrijf.",
        202: "202: Het cv-toestel wacht. Er is vaker dan 1x per 10 minuten een warmtevraag van een aan/uit- of een ModuLine-regeling geweest.",
        305: "305: Het cv-toestel wacht na einde warmwaterbedrijf.",
        353: "353: Het cv-toestel wacht. Het cv-toestel is binnen 24 uur nooit langer dan 20 minuten uit geweest.",
        283: "283: Het cv-toestel  bereidt zich voor op een branderstart. De ventilator en de pomp worden aangestuurd.",
        265: "265: Het cv-toestel wacht. Het cv-toestel schakelt geregeld in op laaglast om aan de warmtevraag te voldoen.",
        203: "203: Het cv-toestel staat stand-by.",
        284: "284: Het gasregelblok wordt aangestuurd.",
        205: "205: Het cv-toestel wacht op het schakelen van de luchtdrukschakelaar.",
        270: "270: Het cv-toestel wordt opgestart.",
        204: "204: Het cv-toestel wacht. De gemeten aanvoertemperatuur is hoger dan de berekende of ingestelde cv-watertemperatuur.",
        276: "276: De aanvoertemperatuursensor heeft een temperatuur gemeten die hoger is dan 95 ºC.",
        277: "277: De safetytemperatuursensor heeft een temperatuur gemeten die hoger is dan 95 ºC.",
        285: "285: De retourtemperatuursensor heeft een temperatuur gemeten die hoger is dan 95 ºC.",
        359: "359: De warmwatertemperatuursensor heeft een te hoge temperatuur gemeten.",
        316: "316: De rookgastemperatuursensor heeft een te hoge temperatuur gemeten.",
        210: "210: De rookgasthermostaat heeft een te hoge temperatuur gemeten en staat geopend.",
        346: "346: De temperatuur van de rookgastemperatuursensor stijgt te snel.",
        317: "317: De contacten van de rookgastemperatuursensor zijn kortgesloten.",
        318: "318: De contacten van de rookgastemperatuursensor zijn onderbroken.",
        343: "343: Tijdens cv-bedrijf: de rookgastemperatuursensor meet een temperatuurstijging, maar de aanvoertemperatuursensor niet.",
        344: "344: Tijdens warmwaterbedrijf: de rookgastemperatuursensor meet een temperatuurstijging, maar de aanvoertemperatuursensor niet.",
        348: "348: Tijdens warmwaterbedrijf: de aanvoertemperatuur is hoger dan 85 ºC.",
        207: "207: De cv-waterdruk is te laag.",
        357: "357: Het ontluchtingsprogramma is actief.",
        260: "260: De aanvoertemperatuursensor meet geen temperatuurstijging na een branderstart.",
        271: "271: Het gemeten temperatuursverschil  tussen de aanvoer- en safetytemperatuursensor is te groot.",
        338: "338: Branderstart te vaak afgebroken.",
        345: "345: De aanvoertemperatuursensor meet geen temperatuurstijging na een branderstart.",
        358: "358: De 3-wegklep wordt gedeblokkeerd.",
        266: "266: De pomptest is mislukt.",
        329: "329: De druksensor meet geen waterstroming.",
        212: "212: De gemeten temperatuur door de aanvoertemperatuursensor of de safetytemperatuursensor, stijgt te snel.",
        341: "341: De gemeten temperatuur door de aanvoertemperatuursensor of de retourtemperatuursensor, stijgt te snel.",
        342: "342: De gemeten temperatuur door de aanvoertemperatuursensor stijgt te snel.",
        213: "213: De gemeten temperatuur tussen de aanvoer- en de retourtemperatuursensor is te groot.",
        349: "349: Het op laaglast gemeten temperatuurverschil tussen de aanvoertemperatuursensor en de retourtemperatuursensor is te groot.",
        281: "281: De pomp zit vast of draait in lucht.",
        282: "282: Het stuursignaal van de pomp ontbreekt.",
        264: "264: Het stuursignaal of de spanning van de ventilator is tijdens bedrijf weggevallen.",
        217: "217: Het ventilatortoerental is onregelmatig tijdens het opstarten.",
        273: "273: Het cv-toestel is maximaal 2 minuten uitgeschakeld geweest, omdat het cv-toestel gedurende 24 uur continu in bedrijf is geweest. Dit is een veiligheidscontrole.",
        214: "214: Ventilator draait niet tijdens de opstartfase (0C).",
        216: "216: Het ventilatortoerental is te laag.",
        215: "215: Het ventilatortoerental is te hoog.",
        218: "218: De aanvoertemperatuursensor heeft een temperatuur gemeten die hoger is dan 105 ºC.",
        332: "332: De aanvoertemperatuursensor heeft een temperatuur gemeten die hoger is dan 110 ºC.",
        224: "224: Een toestelthermostaat (bv. maximaal- of branderthermostaat) heeft een te hoge temperatuur gemeten en staat geopend.",
        225: "225: Er is een overwacht groot temperatuurverschil gemeten in de dubbelsensor.",
        278: "278: De sensortest is mislukt.",
        347: "347: De retourtemperatuursensor heeft een hogere cv-watertemperatuur gemeten dan de aanvoertemperatuursensor. Na 10 minuten volgt een herstart.",
        375: "375: De contacten de externe sensor (bv. solar-sensor) zijn kortgesloten.",
        376: "376: De contacten de externe sensor (bv. solar-sensor) zijn onderbroken.",
        219: "219: De safetytemperatuursensor heeft een temperatuur gemeten die hoger is dan 105 ºC.",
        220: "220: De contacten van de safetytemperatuursensor zijn kortgesloten of de safetytemperatuursensor heeft een temperatuur gemeten die hoger is dan 130 ºC.",
        221: "221: De contacten van de safetytemperatuursensor zijn onderbroken.",
        222: "222: De contacten de aanvoertemperatuursensor zijn kortgesloten.",
        350: "350: De contacten de aanvoertemperatuursensor zijn kortgesloten.",
        522: "522: Er wordt een sensortest uitgevoerd. Het cv-toestel wacht totdat de test is geslaagd.",
        552: "552: Er is, vaker dan is toegestaan, een reset uitgevoerd door een op het cv-toestel aangesloten regeling of kamerthermostaat.",
        509: "509: De branderautomaat is defect.",
        550: "550: De netspanning is te laag.",
        554: "554: De branderautomaat ziet een interne fout.",
        657: "657: De branderautomaat ziet een interne fout.",
        223: "223: De contacten van de aanvoertemperatuursensor zijn onderbroken.",
        351: "351: De contacten van de aanvoertemperatuursensor zijn onderbroken.",
        -6: "-6: Door Nefit Service Tool/Handterminal gegenereerde storingscode.",
        226: "226: Service Tool is aangesloten geweest.",
        -1: "-1: Service Tool: servicetest duurt te lang.",
        268: "268: Componententest.",
        -2: "-2: Service Tool: servicetest duurt te lang of  een het cv-toestelparameter is gewijzigd.",
        227: "227: Er is onvoldoende ionisatiestroom gemeten na het ontsteken van de brander.",
        228: "228: Er is een ionisatiestroom gemeten voordat de brander is gestart.",
        306: "306: Er is een ionisatiestroom gemeten, nadat de brander gedoofd is.",
        -7: "-7: Ionisatie valt weg kort na het ontsteken van de brander.",
        229: "229: Er is onvoldoende ionisatiestroom gemeten tijdens het branden.",
        269: "269: De ontstekingsunit is te lang aangestuurd.",
        -8: "-8: De netspanning of ModuLine thermostaat wordt extern beïnvloed.",
        231: "231: De netspanning is tijdens een vergrendelende storing onderbroken geweest.",
        -9: "-9: Zekering F3 is defect",
        328: "328: Er is een kortstondige onderbreking van de netspanning geweest.",
        261: "261: De branderautomaat is defect.",
        280: "280: De branderautomaat is defect.",
        373: "373: De branderthermostaat heeft, vaker dan is toegestaan, een te hoge temperatuur gemeten.",
        374: "374: Er is,  vaker dan toegestaan, onvoldoende ionisatiestroom gemeten tijdens het branden.",
        364: "364: Het gasregelblok vertoont symptomen van veroudering.",
        365: "365: Het gasregelblok vertoont symptomen van veroudering.",
        232: "232: Het externe schakelcontact is geopend.",
        235: "235: De KIM is te nieuw voor de branderautomaat.",
        360: "360: De geplaatste KIM correspondeert niet met de branderautomaat.",
        361: "361: De geplaatste branderautomaat correspondeert niet met de KIM.",
        322: "322: De branderautomaat ziet geen KIM.",
        -10: "-10: De branderautomaat ziet geen KIM.",
        -11: "-11: De branderautomaat is defect.",
        237: "237: De branderautomaat of de KIM is defect.",
        267: "267: De branderautomaat of de KIM is defect.",
        272: "272: De branderautomaat of de KIM is defect.",
        234: "234: De contacten van het gasregelblok zijn onderbroken.",
        238: "238: De branderautomaat of de KIM is defect.",
        239: "239: De branderautomaat of de KIM is defect.",
        233: "233: De branderautomaat of de KIM is defect.",
        288: "288: De waterdruk is te hoog of de contacten van de druksensor zijn onderbroken.",
        289: "289: De contacten van de druksensor zijn kortgesloten.",
        286: "286: De retourtemperatuursensor heeft een cv-retourtemperatuur gemeten die hoger is dan 105 ºC.",
        240: "240: De contacten van de retourtemperatuursensor zijn kortgesloten.",
        241: "241: De contacten van de retourtemperatuursensor zijn onderbroken.",
        242: "242: De branderautomaat of de KIM is defect.",
        243: "243: De branderautomaat of de KIM is defect.",
        244: "244: De branderautomaat of de KIM is defect.",
        245: "245: De branderautomaat of de KIM is defect.",
        247: "247: De branderautomaat of de KIM is defect.",
        248: "248: De branderautomaat of de KIM is defect.",
        249: "249: De branderautomaat of de KIM is defect.",
        255: "255: De branderautomaat of de KIM is defect.",
        257: "257: De branderautomaat of de KIM is defect.",
        246: "246: De branderautomaat of de KIM is defect.",
        252: "252: De branderautomaat of de KIM is defect.",
        253: "253: De branderautomaat of de KIM is defect.",
        251: "251: De branderautomaat of de KIM is defect.",
        256: "256: De branderautomaat of de KIM is defect.",
        254: "254: De branderautomaat of de KIM is defect.",
        250: "250: De branderautomaat of de KIM is defect.",
        258: "258: De branderautomaat of de KIM is defect.",
        262: "262: De branderautomaat of de KIM is defect.",
        259: "259: De branderautomaat of de KIM is defect.",
        279: "279: De branderautomaat of de KIM is defect.",
        290: "290: De branderautomaat of de KIM is defect.",
        287: "287: De branderautomaat of de KIM is defect.",
        263: "263: De branderautomaat of de KIM is defect.",
        800: "800: De buitentemperatuursensor is defect of geeft een onrealistische waarde.",
        808: "808: De warmwatertemperatuursensor van de eerste ww-groep is defect of geeft een onrealistische waarde.",
        809: "809: De warmwatertemperatuursensor van de tweede ww-groep is defect of geeft een onrealistische waarde.",
        810: "810: De warmwatervoorziening blijft koud of de warmwatertemperatuur is tijdens opwarming gedurende 2 uur niet gestegen.",
        811: "811: De thermische desinfectie van de warmwaterboiler is niet gelukt of de temperatuur voor het desinfecteren van de warmwaterboiler is niet gehaald binnen 3 uur.",
        816: "816: Er is geen communicatie mogelijk over de communicatiebus.",
        828: "828: Waterdruksensor geeft storing.",
        816: "816: Geen communicatie met het bedieningspaneel van de cv-ketel.",
        801: "801: Er is een interne fout opgetreden.",
        802: "802: De tijd is niet ingesteld.",
        803: "803: De datum is niet ingesteld.",
        804: "804: Er is een interne fout opgetreden.",
        806: "806: De ruimtetemperatuursensor van de ModuLine-regeling is defect of geeft een onrealistische waarde.",
        821: "821: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        822: "822: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        823: "823: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        824: "824: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        825: "825: Er zijn 2 ModuLine-regelingen toegekend aan 1 cv-groep.",
        826: "826: De ruimtetemperatuursensor van de ModuLine 400 regeling is defect of geeft onrealistische waarde.",
        827: "827: De ruimtetemperatuursensor van de ModuLine 400 regeling is defect of geeft onrealistische waarde.",
        828: "828: De waterdruksensor is defect of geeft onrealistische waarde.",
        815: "815: De aanvoertemperatuursensor van de open verdeler is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de verdelermodule (WM10).",
        825: "825: Er zijn 2 ModuLine-regelingen toegekend aan 1 cv-groep.",
        806: "806: De ruimtetemperatuursensor van de ModuLine-regeling van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de ModuLine-regeling van de betreffende cv-groep.",
        829: "829: Er is geen cv-groep toegekend aan de ModuLine-regeling, of er is een cv-groep toegekend aan een niet aanwezige ModuLine-regeling.",
        830: "830: Er is een te lage batterijspanning voor de draadloze ModuLine-regeling van de betreffende cv-groep.",
        839: "839: Er is geen radiocommunicatie met de draadloze ModuLine-regeling van de betreffende cv-groep.",
        842: "842: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        843: "843: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        806: "806: De ruimtetemperatuursensor van de ModuLine-regeling van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de ModuLine-regeling van de betreffende cv-groep.",
        829: "829: Er is geen cv-groep toegekend aan de ModuLine-regeling, of er is een cv-groep toegekend aan een niet aanwezige ModuLine-regeling.",
        830: "830: Er is een te lage batterijspanning voor de draadloze ModuLine-regeling van de betreffende cv-groep.",
        839: "839: Er is geen radiocommunicatie met de draadloze ModuLine-regeling van de betreffende cv-groep.",
        842: "842: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        843: "843: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        806: "806: De ruimtetemperatuursensor van de ModuLine-regeling van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de ModuLine-regeling van de betreffende cv-groep.",
        829: "829: Er is geen cv-groep toegekend aan de ModuLine-regeling, of er is een cv-groep toegekend aan een niet aanwezige ModuLine-regeling.",
        830: "830: Er is een te lage batterijspanning voor de draadloze ModuLine-regeling van de betreffende cv-groep.",
        839: "839: Er is geen radiocommunicatie met de draadloze ModuLine-regeling van de betreffende cv-groep.",
        842: "842: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        843: "843: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        806: "806: De ruimtetemperatuursensor van de ModuLine-regeling van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de ModuLine-regeling van de betreffende cv-groep.",
        829: "829: Er is geen cv-groep toegekend aan de ModuLine-regeling, of er is een cv-groep toegekend aan een niet aanwezige ModuLine-regeling.",
        830: "830: Er is een te lage batterijspanning voor de draadloze ModuLine-regeling van de betreffende cv-groep.",
        839: "839: Er is geen radiocommunicatie met de draadloze ModuLine-regeling van de betreffende cv-groep.",
        842: "842: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        843: "843: Er is geen ModuLine-regeling toegepast voor de betreffende cv-groep.",
        807: "807: De aanvoertemperatuursensor van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de mengklepmodule (MM10) van de betreffende cv-groep.",
        807: "807: De aanvoertemperatuursensor van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de mengklepmodule (MM10) van de betreffende cv-groep.",
        807: "807: De aanvoertemperatuursensor van de betreffende cv-groep is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de mengklepmodule (MM10) van de betreffende cv-groep.",
        812: "812: De zonneboilerregeling is verkeerd ingesteld.",
        813: "813: De collectortemperatuursensor is defect of geeft een onrealistische waarde.",
        814: "814: De zonneboilertemperatuursensor is defect of geeft een onrealistische waarde.",
        816: "816: Er is geen communicatie mogelijk met de zonneboilermodule (SM10).",
        817: "817: De luchttemperatuursensor is defect of geeft onrealistische waarde.",
        818: "818: De aanvoertemperatuur van het cv-toestel stijgt te weinig binnen 30 minuten.",
        819: "819: Niet van toepassing op gasgestookte cv-toestellen.",
        820: "820: Niet van toepassing op gasgestookte cv-toestellen.",
        -13: "-13: De rookgastemperatuur is hoger dan normaal.",
        -14: "-14: De ventilator draait langzamer dan normaal.",
        -15: "-15: Het aantal bedrijfsuren voor de volgende onderhoudsbeurt is verlopen.",
        -17: "-17: Onderhoudsmelding: de ionisatiestroom is lager dan normaal.",
        -18: "-18: Onderhoudsmelding: de ontsteekspanning is hoger dan normaal.",
        -19: "-19: Onderhoudsmelding: het aantal herstarts voor het in bedrijf brengen van de brander is meer dan normaal.",
        -20: "-20: De  gemeten cv-waterdruk is te laag.  Het vermogen voor zowel cv-bedrijf als voor warmwaterbedrijf wordt beperkt.",
        -21: "-21: De ingestelde onderhoudsdatum  is verlopen. Onderhoud gewenst.",
        -25: "-25: De warmwateruitstroomtemperatuursensor is defect. De functie wordt overgenomen door de software van het cv-toestel.",
        -26: "-26: De bewaartemperatuursensor is defect. De functie wordt overgenomen door de software van het cv-toestel.",
        -27: "-27: De ingestelde maximale onderhoudsperiode, is overschreden. Onderhoud gewenst.",
        -28: "-28: Onderhoudsperiode is ingesteld.",
        -40: "-40: De contacten van de druksensor zijn onderbroken.",
        -48: "-48: Het cv-toestel wordt gereset.",
        -4: "-4: Het cv-toestel wordt gereset.",
    }
    if code in cause_codes:
        return cause_codes[code]

    return code
