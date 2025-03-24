from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.views import APIView
from drfasyncview import AsyncAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async, async_to_sync
import re
import json
from openai import AsyncOpenAI
from bs4 import BeautifulSoup
from django.db import models, connection
import os
import tiktoken
from django.http import JsonResponse
from .models import *
from django.http import StreamingHttpResponse
from django.db.models import Q, F
from pydantic import BaseModel
import asyncio
from pathlib import Path
from ipware import get_client_ip
from difflib import SequenceMatcher
import ast
import twilio
from twilio.rest import Client
import pandas as pd
import time

TWILIO_ACCOUNT_SID = os.environ.get("TWILIOSID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIOAUTHTOKEN")
semaphore = asyncio.Semaphore(10)

class MainApp(AsyncAPIView):
    permission_classes = [AllowAny]
    async def post(self, request, *args, **kwargs):
        file = request.FILES.get('file') if request.FILES.get('file') else None
        if file is None:
            return Response({"success": False, "message": "File can't be empty!"}, status=status.HTTP_400_BAD_REQUEST)
        df = pd.read_excel(file)
        headers = list(df)
        requirements = ["nama", "mobile_phone", "limit_indikatif"]
        filtered_data = df[df["limit_indikatif"] > 1500000000]
        if all(req in headers for req in requirements):
            print("All is cool my man")
            #data = {req: df[req].tolist() for req in requirements}
            data = {req: filtered_data[req].tolist() for req in requirements}
            return Response({"success": True, "message": "File successfuly parsed", "data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "message": "Column headers are missing"}, status=status.HTTP_400_BAD_REQUEST)
    
    async def get(self, request):
        return render(request, "index.html")
    
@csrf_exempt
async def start_message(request):
    print(request.body)
    #data = ast.literal_eval(request.body)
    data = json.loads(request.body)
    names = data.get("nama", [])
    numbers = data.get("mobile_phone", [])
    limits = data.get("limit_indikatif", [])
    upload_start = time.time()
    result = await asyncio.gather(
        *[send_whatsapp_message(name, number, limit) for name, number, limit in zip(names, numbers, limits)],
        return_exceptions=True
    )
    end_time = time.time()
    print(f"Combining excel etc. time: {end_time - upload_start:.2f} seconds")
    if any(r is False for r in result):
        return JsonResponse({"success": False, "message": f"Error processing message"})
    return JsonResponse({"success": True, "message": f"Successfuly messaged {len(result)} customers", "status": status.HTTP_200_OK})

async def send_whatsapp_message(name, number, limit):
    async with semaphore:
        try:
            upload_start = time.time()
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                from_='whatsapp:+14155238886',
                body=f'Hello {name}, your limit for KKB is: {limit}. You can find out more on livin by mandiri app',
                to=f'whatsapp:+{number}'
            )
            end_time =time.time()
            print(f"Sent to {name} ({number}): {message.sid} within {end_time - upload_start:.2f} seconds")
            return True
        except Exception as e:
            print(f"Failed to send to {name} ({number}): {e}")
            return False
        
import logging

logger = logging.getLogger(__name__)

class KPRCalculator(AsyncAPIView):
    permission_classes = [AllowAny]

    async def post(self, request, *args, **kwargs):
        try:
            input = request.data.get('input')
            userid = request.data.get('userid')

            if input is None or userid is None:
                return Response({"success": False, "message": "Input tidak boleh kosong!"}, status=status.HTTP_400_BAD_REQUEST)

            query = await sync_to_async(lambda: userData.objects.filter(userid=userid).last())()
            
            if not query:
                return Response({"success": False, "message": "User tidak ditemukan!"}, status=status.HTTP_404_NOT_FOUND)

            input = int(request.data.get('input'))
            cicilan_tetap = int(query.cicilanperbulan)
            tenor = await self.hitung_tenor_baru(input, 0.0077, cicilan_tetap)
            sisa_bade = query.remaining_debt
            fresh_money = input - query.remaining_debt

            return Response({
                "success": True,
                "tenor": tenor,
                "cicilan_per_bulan": cicilan_tetap,
                "fresh_money": fresh_money,
                "bunga": 9.25,
                "KSM_sebelumnya": query.ksm_old,
                "sisa_baki_debet": sisa_bade,
                "cicilan_sebelumnya": cicilan_tetap 
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error saat menghitung KSM: {str(e)}")
            return Response({"success": False, "message": f"Terjadi error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    async def get(self, request):
        #userid = request.data.get("userid") if request.data.get('userid') else None
        #userid = await sync_to_async(lambda: userData.objects.filter())
        context = {}
        return render(request, "KSMCalculator.html", context)
    
    async def hitung_tenor_baru(self, P, r, A):
        print((P*r)/A)
        import math
        if A <= 0:
            raise ValueError("A must be greater than 0")
        if r <= -1:
            raise ValueError("r must be greater than -1")
        if (P * r) / A >= 1:
            raise ValueError("Invalid values: (P * r) / A must be less than 1")
        n = math.log(1 - (P * r) / A) / math.log(1 + r)
        return abs(round(n))
    
class LoginView(AsyncAPIView):
    permission_classes = [AllowAny]
    async def post(self, request, *args, **kwargs):
        userid = request.data.get('userid') if request.data.get('userid') else None
        if userid is None:
            return Response({"success": False, "message": "Input can't be empty"}, status=status.HTTP_400_BAD_REQUEST)
        userid_query = await sync_to_async(lambda: userData.objects.filter(userid=userid).first().userid)()
        if userid_query is None:
            return Response({"success": False, "message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "userid": userid}, status=status.HTTP_200_OK)
        
    async def get(self, request):
        return render(request, "login.html")

@csrf_exempt
def add_data(request):
    file = request.FILES.get('file') if request.FILES.get('file') else None
    df = pd.read_excel(file)
    data_list = [
        {
            'userid': int(str(row['tanggal_lahir'])),
            'ksm_old': row['Pinjaman_Awal'],
            #'ksm_new': row['Pinjaman Baru (Bebas Input)'],
            'cicilanperbulan': row['Cicilan_per_bulan'],
            'nama_nasabah': row['Nama_Nasabah'],
            'tenor_old': row['Tenor_Awal'],
            'tenor_new': row['Tenor (Bulan)'],
            'interest_old': int(row['Bunga_Awal'] * 100),
            'interest_new': int(row['Bunga'] * 100),
            'remaining_debt': row['Sisa_Baki_Debet']
        }
        for _, row in df.iterrows()
    ]
    print(data_list)
    object = [userData(**entry) for entry in data_list]
    result = userData.objects.bulk_create(object)
    #result = await sync_to_async(lambda: userData.objects.acreate(**data))()
    print(result)
    return JsonResponse({"success": True})